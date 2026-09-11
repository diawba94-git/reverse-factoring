import { apiFetch } from "./apiClient";

export type CauseLitige = "cheque_sans_provision" | "contestation_acheteur" | "ecart_remboursement" | "autre";
export type StatutLitige = "ouvert" | "en_cours" | "resolu";
export type ActionLitige = "contacter_parties" | "engager_recouvrement" | "proposer_resolution" | "marquer_resolu";

export type LitigeOut = {
  id: string;
  facture_id: string;
  numero_facture: string | null;
  fournisseur: string;
  acheteur: string;
  partenaire_concerne: string | null;
  cause: CauseLitige;
  montant_en_jeu: string;
  description: string;
  statut: StatutLitige;
  derniere_action: string | null;
  resolution_note: string | null;
  ouvert_le: string;
  resolu_le: string | null;
};

export function listerLitiges(filtres: { statut?: StatutLitige; cause?: CauseLitige }, token: string) {
  const params = new URLSearchParams();
  if (filtres.statut) params.set("statut", filtres.statut);
  if (filtres.cause) params.set("cause", filtres.cause);
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<LitigeOut[]>(`/litiges${query}`, { token });
}

export function agirSurLitige(litigeId: string, action: ActionLitige, resolutionNote: string | undefined, token: string) {
  return apiFetch<LitigeOut>(`/litiges/${litigeId}`, {
    method: "PATCH",
    body: { action, resolution_note: resolutionNote },
    token,
  });
}
