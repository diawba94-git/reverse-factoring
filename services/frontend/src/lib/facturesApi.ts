import { apiFetch } from "./apiClient";

export type LigneFactureOut = {
  id: string;
  ordre: number;
  designation: string;
  description: string | null;
  quantite: string;
  prix_unitaire: string;
  montant_ligne: string;
};

export type PremiereValidationInfo = {
  nom: string | null;
  role_validateur: "validateur_1" | "validateur_2";
  date_validation: string;
};

export type FactureOut = {
  id: string;
  numero_facture: string | null;
  pme_id: string;
  donneur_ordre_id: string;
  premiere_validation: PremiereValidationInfo | null;
  historique_validations: PremiereValidationInfo[];
  montant_ht: string;
  taux_tva: string;
  montant_tva: string;
  montant_ttc: string;
  devise: string;
  date_emission: string;
  date_echeance: string;
  duree_jours: number;
  statut: string;
  piece_justificative_url: string;
  description: string | null;
  source_creation: string;
  ninea_emetteur_extrait: string | null;
  code_validation_dgid: string | null;
  conformite_verifiee: boolean;
  motifs_rejet_conformite: string[] | null;
  created_at: string;
  lignes: LigneFactureOut[];
};

export type DonneurOrdreOut = {
  id: string;
  raison_sociale: string;
  type: string;
};

export function listerDonneursOrdre(token: string) {
  return apiFetch<DonneurOrdreOut[]>("/entreprises?type=GRANDE_ENTREPRISE", { token });
}

export type LigneFacturePayload = {
  designation: string;
  description?: string | null;
  quantite: string;
  prix_unitaire: string;
};

export type FactureNativePayload = {
  donneur_ordre_id: string;
  date_emission: string;
  date_echeance: string;
  taux_tva: string;
  notes?: string | null;
  lignes: LigneFacturePayload[];
  pme_id?: string;
};

export function creerFactureNative(payload: FactureNativePayload, token: string) {
  return apiFetch<FactureOut>("/factures/native", { method: "POST", body: payload, token });
}

export function obtenirFacture(factureId: string, token: string) {
  return apiFetch<FactureOut>(`/factures/${factureId}`, { token });
}

export function modifierLignesFacture(factureId: string, lignes: (LigneFacturePayload & { id?: string })[], token: string) {
  return apiFetch<FactureOut>(`/factures/${factureId}/lignes`, { method: "PATCH", body: { lignes }, token });
}

export function transmettreFacture(factureId: string, token: string) {
  return apiFetch<FactureOut>(`/factures/${factureId}/transmettre`, { method: "POST", token });
}

export function supprimerFacture(factureId: string, token: string) {
  return apiFetch<void>(`/factures/${factureId}`, { method: "DELETE", token });
}

export type LigneFactureExtraiteOut = {
  designation: string;
  quantite: string;
  prix_unitaire: string;
};

export type FactureExtractionOut = {
  via_ocr: boolean;
  numero_facture: string | null;
  date_emission: string | null;
  date_echeance: string | null;
  taux_tva: string | null;
  montant_ht: string | null;
  montant_tva: string | null;
  montant_ttc: string | null;
  lignes: LigneFactureExtraiteOut[];
  avertissements: string[];
};

export function extraireFacturePourCreation(fichier: File, token: string) {
  const form = new FormData();
  form.append("fichier", fichier);
  return apiFetch<FactureExtractionOut>("/factures/extraction-ocr", { method: "POST", body: form, isFormData: true, token });
}

export type FacturesFiltres = {
  pme_id?: string;
  donneur_ordre_id?: string;
  numero?: string;
  statut?: string;
};

export function listerFactures(filtres: FacturesFiltres, token: string) {
  const params = new URLSearchParams();
  if (filtres.pme_id) params.set("pme_id", filtres.pme_id);
  if (filtres.donneur_ordre_id) params.set("donneur_ordre_id", filtres.donneur_ordre_id);
  if (filtres.numero) params.set("numero", filtres.numero);
  if (filtres.statut) params.set("statut", filtres.statut);
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<FactureOut[]>(`/factures${query}`, { token });
}
