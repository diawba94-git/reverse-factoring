import { apiFetch } from "./apiClient";

export type RemboursementSuperviseOut = {
  id: string;
  avance_id: string;
  montant_recu: string;
  date_reception: string;
  source_entreprise: string;
  montant_attendu: string;
  ecart: string;
  statut_rapprochement: "en_attente" | "rapproche" | "ecart_detecte";
};

export function rapprocherRemboursement(
  remboursementId: string,
  statut: "rapproche" | "ecart_detecte",
  token: string,
) {
  return apiFetch<{ statut_rapprochement: string }>(`/remboursements/${remboursementId}/rapprocher`, {
    method: "POST",
    body: { statut_rapprochement: statut },
    token,
  });
}
