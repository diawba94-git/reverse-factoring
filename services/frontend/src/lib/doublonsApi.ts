import { apiFetch } from "./apiClient";

export type DoublonEntrepriseOut = {
  id: string;
  raison_sociale: string;
  statut_fiche: "pre_inscrite" | "active";
  statut_kyc: "en_attente" | "valide" | "rejete";
  contact_telephone: string;
  cree_par: string | null;
  nombre_factures: number;
};

export type DoublonCandidatOut = {
  conserver: DoublonEntrepriseOut;
  fusionner: DoublonEntrepriseOut;
  score_similarite: number;
  critere: string;
};

export type FusionDoublonResultOut = {
  conserver_id: string;
  fusionner_id: string;
  factures_reassignees: number;
  utilisateurs_reassignes: number;
};

export function detecterDoublons(token: string) {
  return apiFetch<DoublonCandidatOut[]>("/admin/doublons/detecter", { token });
}

export function fusionnerDoublons(conserverId: string, fusionnerId: string, token: string) {
  return apiFetch<FusionDoublonResultOut>("/admin/doublons/fusionner", {
    method: "POST",
    body: { conserver_id: conserverId, fusionner_id: fusionnerId },
    token,
  });
}
