import { apiFetch } from "./apiClient";

export type JournalAuditOut = {
  id: string;
  entite_type: string;
  entite_id: string;
  action: string;
  utilisateur_id: string | null;
  horodatage: string;
  valeur_avant: Record<string, unknown> | null;
  valeur_apres: Record<string, unknown>;
};

export function listerJournalAudit(
  filtres: { entite_type?: string; action?: string },
  token: string,
) {
  const params = new URLSearchParams();
  if (filtres.entite_type) params.set("entite_type", filtres.entite_type);
  if (filtres.action) params.set("action", filtres.action);
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<JournalAuditOut[]>(`/admin/journal-audit${query}`, { token });
}
