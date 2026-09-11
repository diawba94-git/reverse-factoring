import { apiFetch } from "./apiClient";

export type TypePartenaire = "banque" | "imf";

export type GrilleTarifaireOut = {
  id: string;
  nom: string;
  taux_total_minimum: string;
  taux_total_maximum: string;
  proportion_cedra: string;
  proportion_partenaire: string;
  plafond_montant: string | null;
  duree_minimum_jours: number;
  duree_maximum_jours: number;
  taux_avance: string;
  type_partenaire: TypePartenaire;
  active: boolean;
  date_debut_validite: string;
  date_fin_validite: string | null;
};

export type GrilleTarifairePayload = {
  nom: string;
  taux_total_minimum: string;
  taux_total_maximum: string;
  proportion_cedra: string;
  proportion_partenaire: string;
  plafond_montant?: string | null;
  duree_minimum_jours: number;
  duree_maximum_jours: number;
  taux_avance: string;
  type_partenaire: TypePartenaire;
  active: boolean;
  date_debut_validite: string;
  date_fin_validite?: string | null;
};

export type GrilleTarifaireUpdatePayload = Partial<GrilleTarifairePayload>;

export function listerGrilles(token: string) {
  return apiFetch<GrilleTarifaireOut[]>("/grilles-tarifaires", { token });
}

export function listerGrillesActives(token: string) {
  return apiFetch<GrilleTarifaireOut[]>("/grilles-tarifaires/actives", { token });
}

export function creerGrille(payload: GrilleTarifairePayload, token: string) {
  return apiFetch<GrilleTarifaireOut>("/grilles-tarifaires", { method: "POST", body: payload, token });
}

export function modifierGrille(id: string, payload: GrilleTarifaireUpdatePayload, token: string) {
  return apiFetch<GrilleTarifaireOut>(`/grilles-tarifaires/${id}`, { method: "PUT", body: payload, token });
}
