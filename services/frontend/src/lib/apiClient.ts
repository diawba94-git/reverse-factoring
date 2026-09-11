export const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type PydanticValidationItem = {
  loc: (string | number)[];
  msg: string;
};

export class ApiError extends Error {
  status: number;
  fieldErrors: Record<string, string>;

  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(message);
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

function parseErrorBody(status: number, body: unknown): ApiError {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;

    if (typeof detail === "string") {
      return new ApiError(status, detail);
    }

    if (Array.isArray(detail)) {
      const fieldErrors: Record<string, string> = {};
      const messages: string[] = [];
      for (const item of detail as PydanticValidationItem[]) {
        const field = item.loc?.[item.loc.length - 1];
        if (typeof field === "string") {
          fieldErrors[field] = item.msg;
        }
        messages.push(item.msg);
      }
      return new ApiError(status, messages[0] ?? "Requête invalide.", fieldErrors);
    }
  }

  return new ApiError(status, "Une erreur inattendue est survenue. Veuillez réessayer.");
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  token?: string | null;
  isFormData?: boolean;
};

export type PageResult<T> = { items: T[]; total: number };

/** Comme apiFetch, mais pour un endpoint pagine (params page/per_page deja inclus dans
 * `path`) : lit le total depuis l'entete X-Total-Count plutot que de changer la forme du
 * corps de reponse (qui reste un simple tableau, compatible avec les appelants non
 * pagines du meme endpoint — voir les routers backend concernes). */
export async function apiFetchPaginated<T>(path: string, token?: string | null): Promise<PageResult<T>> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  } catch {
    throw new ApiError(0, "Impossible de joindre le serveur. Vérifiez votre connexion.");
  }

  const text = await response.text();
  const parsed = text ? JSON.parse(text) : null;

  if (!response.ok) {
    throw parseErrorBody(response.status, parsed);
  }

  const items = (parsed as T[]) ?? [];
  const totalHeader = response.headers.get("X-Total-Count");
  return { items, total: totalHeader !== null ? Number(totalHeader) : items.length };
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, token, isFormData = false } = options;

  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (!isFormData && body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: isFormData ? (body as FormData) : body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "Impossible de joindre le serveur. Vérifiez votre connexion.");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  const parsed = text ? JSON.parse(text) : null;

  if (!response.ok) {
    throw parseErrorBody(response.status, parsed);
  }

  return parsed as T;
}
