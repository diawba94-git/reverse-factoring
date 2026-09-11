import { apiFetch } from "./apiClient";
import type { EntrepriseOut } from "./adminApi";

export type EntrepriseLegereOut = {
  id: string;
  raison_sociale: string;
  type: string;
};

export function listerEntreprisesParType(type: "PME" | "GRANDE_ENTREPRISE" | "PARTENAIRE_FINANCIER", token: string) {
  return apiFetch<EntrepriseLegereOut[]>(`/entreprises?type=${type}`, { token });
}

export function obtenirEntreprise(id: string, token: string) {
  return apiFetch<EntrepriseOut>(`/entreprises/${id}`, { token });
}

export type DashboardPmeOut = {
  nombre_factures: number;
  montant_total_factures: string;
  factures_par_statut: Record<string, number>;
  nombre_avances_actives: number;
  montant_total_avance_percu: string;
  montant_total_solde_du: string;
};

export function obtenirDashboardPme(pmeId: string, token: string) {
  return apiFetch<DashboardPmeOut>(`/dashboard/pme/${pmeId}`, { token });
}

export type NotificationPmeOut = {
  type: "validation" | "financement" | "litige" | "acheteur" | "kyc" | "invitation";
  titre: string;
  description: string;
  date: string;
  lu: boolean;
};

export function listerNotificationsPme(token: string) {
  return apiFetch<NotificationPmeOut[]>("/pme/notifications", { token });
}

export type GrilleTarifaireOut = {
  id: string;
  nom: string;
  duree_minimum_jours: number;
  duree_maximum_jours: number;
  taux_avance: string;
};

export function listerGrillesActives(token: string) {
  return apiFetch<GrilleTarifaireOut[]>("/grilles-tarifaires/actives", { token });
}

export type SimulationFraisPayload = {
  montant: string;
  duree_jours: number;
  grille_tarifaire_id?: string;
};

export type SimulationFraisResultat = {
  montant_avance_initial: string;
  montant_solde_du: string;
  frais_total: string;
  taeg_annualise: string;
  grille_utilisee: string;
};

export function simulerFrais(payload: SimulationFraisPayload, token: string) {
  return apiFetch<SimulationFraisResultat>("/simulation/frais", { method: "POST", body: payload, token });
}

export type AvanceOut = {
  id: string;
  facture_id: string;
  partenaire_financier_id: string;
  grille_tarifaire_id: string;
  montant_avance_initial: string;
  frais_total: string;
  montant_solde_du: string;
  part_partenaire: string;
  part_plateforme: string;
  taeg_annualise: string;
  date_versement_initial: string | null;
  date_versement_solde: string | null;
  statut: string;
  methode_versement: string;
  garantie_detenue_avant_financement: boolean;
  created_at: string;
};

export function listerAvances(pmeId: string, token: string) {
  return apiFetch<AvanceOut[]>(`/avances?pme_id=${encodeURIComponent(pmeId)}`, { token });
}

export function listerToutesAvances(filtres: { statut?: string; partenaire_financier_id?: string }, token: string) {
  const params = new URLSearchParams();
  if (filtres.statut) params.set("statut", filtres.statut);
  if (filtres.partenaire_financier_id) params.set("partenaire_financier_id", filtres.partenaire_financier_id);
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<AvanceOut[]>(`/avances${query}`, { token });
}

export type AvanceCreatePayload = {
  facture_id: string;
  partenaire_financier_id: string;
  methode_versement: "wave" | "virement_bancaire";
};

export function demanderAvance(payload: AvanceCreatePayload, token: string) {
  return apiFetch<AvanceOut>("/avances", { method: "POST", body: payload, token });
}

export type InviterPayload = {
  telephone: string;
  email: string;
  nom: string;
  role: string;
};

export function inviterCollegue(entrepriseId: string, payload: InviterPayload, token: string) {
  return apiFetch<{ id: string; token: string; expires_at: string }>(`/entreprises/${entrepriseId}/inviter`, {
    method: "POST",
    body: payload,
    token,
  });
}
