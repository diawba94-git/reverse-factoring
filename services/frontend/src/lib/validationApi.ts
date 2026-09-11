import { apiFetch } from "./apiClient";
import type { FactureOut } from "./facturesApi";

export function valider(factureId: string, token: string, commentaire?: string) {
  return apiFetch<FactureOut>(`/factures/${factureId}/valider`, {
    method: "POST",
    body: { commentaire: commentaire ?? null },
    token,
  });
}

export function rejeter(factureId: string, commentaire: string, token: string) {
  return apiFetch<FactureOut>(`/factures/${factureId}/rejeter`, {
    method: "POST",
    body: { commentaire },
    token,
  });
}
