import { apiFetch } from "./apiClient";

export type ArticleFaqOut = {
  id: string;
  question: string;
  reponse: string;
  portee: string;
  publie: boolean;
  created_at: string;
  updated_at: string;
};

export type ArticleFaqPayload = {
  question: string;
  reponse: string;
  portee: string;
  publie?: boolean;
};

export function listerArticlesFaq(token: string) {
  return apiFetch<ArticleFaqOut[]>("/faq", { token });
}

export function creerArticleFaq(payload: ArticleFaqPayload, token: string) {
  return apiFetch<ArticleFaqOut>("/faq", { method: "POST", body: payload, token });
}

export function modifierArticleFaq(id: string, payload: Partial<ArticleFaqPayload>, token: string) {
  return apiFetch<ArticleFaqOut>(`/faq/${id}`, { method: "PUT", body: payload, token });
}

export function supprimerArticleFaq(id: string, token: string) {
  return apiFetch<void>(`/faq/${id}`, { method: "DELETE", token });
}
