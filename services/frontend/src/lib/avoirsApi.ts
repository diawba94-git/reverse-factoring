import { apiFetch, apiFetchPaginated } from "./apiClient";

export type MotifAvoir = "retour_partiel" | "erreur_prix" | "remise_commerciale" | "autre";
export type StatutAvoir = "emis" | "confirme_par_acheteur" | "rejete";
export type StatutCreance = "en_attente" | "partiellement_recouvree" | "soldee";

export type AvoirOut = {
  id: string;
  numero_avoir: string;
  facture_id: string;
  montant_ht: string;
  montant_tva: string;
  montant_ttc: string;
  motif: MotifAvoir;
  statut: StatutAvoir;
  date_emission: string;
  piece_justificative_url: string | null;
  effet_applique: string | null;
  montant_deduit_solde: string | null;
  created_at: string;
};

export type CreanceOut = {
  id: string;
  pme_id: string;
  avoir_id: string;
  montant_du: string;
  montant_recouvre: string;
  statut: StatutCreance;
  date_creation: string;
};

export type AvoirCreatePayload = {
  montant_ht: string;
  montant_tva: string;
  montant_ttc: string;
  motif: MotifAvoir;
  piece_justificative_url?: string | null;
};

export function creerAvoir(factureId: string, payload: AvoirCreatePayload, token: string) {
  return apiFetch<AvoirOut>(`/factures/${factureId}/avoirs`, { method: "POST", body: payload, token });
}

export function confirmerAvoir(avoirId: string, token: string) {
  return apiFetch<AvoirOut>(`/avoirs/${avoirId}/confirmer`, { method: "POST", token });
}

export function rejeterAvoir(avoirId: string, token: string) {
  return apiFetch<AvoirOut>(`/avoirs/${avoirId}/rejeter`, { method: "POST", token });
}

export type AvoirsFiltres = {
  pme_id?: string;
  donneur_ordre_id?: string;
  statut?: StatutAvoir;
  page?: number;
  per_page?: number;
};

export function listerAvoirs(filtres: AvoirsFiltres, token: string) {
  const params = new URLSearchParams();
  if (filtres.pme_id) params.set("pme_id", filtres.pme_id);
  if (filtres.donneur_ordre_id) params.set("donneur_ordre_id", filtres.donneur_ordre_id);
  if (filtres.statut) params.set("statut", filtres.statut);
  if (filtres.page) params.set("page", String(filtres.page));
  if (filtres.per_page) params.set("per_page", String(filtres.per_page));
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<AvoirOut[]>(`/avoirs${query}`, { token });
}

export function listerAvoirsPagines(filtres: AvoirsFiltres, token: string) {
  const params = new URLSearchParams();
  if (filtres.pme_id) params.set("pme_id", filtres.pme_id);
  if (filtres.donneur_ordre_id) params.set("donneur_ordre_id", filtres.donneur_ordre_id);
  if (filtres.statut) params.set("statut", filtres.statut);
  params.set("page", String(filtres.page ?? 1));
  params.set("per_page", String(filtres.per_page ?? 25));
  return apiFetchPaginated<AvoirOut>(`/avoirs?${params.toString()}`, token);
}

export function listerCreancesPme(pmeId: string, token: string) {
  return apiFetch<CreanceOut[]>(`/pme/${pmeId}/creances`, { token });
}

export function listerToutesCreances(token: string) {
  return apiFetch<CreanceOut[]>("/creances", { token });
}
