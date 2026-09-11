import { apiFetch } from "./apiClient";

export type StatutRelation = "pilote" | "convention_signee";
export type StatutCompteDedie = "en_ouverture" | "actif" | "cloture";

export type RelationOut = {
  id: string;
  pme_id: string;
  pme_raison_sociale: string;
  donneur_ordre_id: string;
  donneur_ordre_raison_sociale: string;
  statut: StatutRelation;
  factures_pilote_max: number;
  factures_pilote_utilisees: number;
  date_debut_relation: string;
  compte_dedie_statut: StatutCompteDedie | null;
  nombre_signatures: number;
};

export type RelationResumeOut = {
  pilote: number;
  convention_signee: number;
};

export function obtenirResumeRelations(token: string) {
  return apiFetch<RelationResumeOut>("/relations/resume", { token });
}

export function listerRelations(filtres: { pme_id?: string; donneur_ordre_id?: string }, token: string) {
  const params = new URLSearchParams();
  if (filtres.pme_id) params.set("pme_id", filtres.pme_id);
  if (filtres.donneur_ordre_id) params.set("donneur_ordre_id", filtres.donneur_ordre_id);
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<RelationOut[]>(`/relations${query}`, { token });
}

export function modifierStatutRelation(relationId: string, statut: StatutRelation, token: string) {
  return apiFetch<RelationOut>(`/relations/${relationId}`, { method: "PATCH", body: { statut }, token });
}

export type RelationChipOut = {
  relation_id: string;
  pme_id: string;
  pme_raison_sociale: string;
};

export type ValidateurAvecRelationsOut = {
  utilisateur_id: string;
  nom: string | null;
  role: "validateur_1" | "validateur_2";
  relations: RelationChipOut[];
  relations_en_attente: RelationChipOut[];
};

export function listerValidateursAvecRelations(token: string) {
  return apiFetch<ValidateurAvecRelationsOut[]>("/relations/validateurs", { token });
}

export function signerConvention(
  relationId: string,
  payload: { signature_pme?: boolean; signature_donneur_ordre?: boolean; signature_partenaire?: boolean },
  token: string,
) {
  return apiFetch<RelationOut>(`/relations/${relationId}/convention`, { method: "PATCH", body: payload, token });
}
