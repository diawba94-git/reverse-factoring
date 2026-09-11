import { apiFetch, ApiError, BASE_URL } from "./apiClient";
import type { AvanceOut } from "./pmeApi";

export function listerAvancesPartenaire(filtres: { statut?: string }, token: string) {
  const params = new URLSearchParams();
  if (filtres.statut) params.set("statut", filtres.statut);
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<AvanceOut[]>(`/avances${query}`, { token });
}

export type EnveloppeOut = {
  partenaire_financier_id: string;
  montant_total_alloue: string;
  montant_engage: string;
  montant_disponible: string;
};

export function obtenirMonEnveloppe(token: string) {
  return apiFetch<EnveloppeOut>("/enveloppes/moi", { token });
}

export function approuverAvance(avanceId: string, token: string) {
  return apiFetch<AvanceOut>(`/avances/${avanceId}/approuver`, { method: "POST", token });
}

export function rejeterAvance(avanceId: string, commentaire: string, token: string) {
  return apiFetch<AvanceOut>(`/avances/${avanceId}/rejeter`, { method: "POST", body: { commentaire }, token });
}

export type ChequeResumeOut = {
  numero_cheque: string;
  banque_emettrice: string;
  date_encaissement_prevue: string;
  statut: string;
};

export type DossierDecisionOut = {
  avance: AvanceOut;
  numero_facture: string | null;
  montant_ttc: string;
  date_emission: string;
  date_echeance: string;
  duree_jours: number;
  pme_raison_sociale: string;
  pme_statut_kyc: string;
  donneur_ordre_raison_sociale: string;
  donneur_ordre_statut_kyc: string;
  relation_statut: "pilote" | "convention_signee" | null;
  cheque: ChequeResumeOut | null;
  enveloppe_disponible: string | null;
  enveloppe_totale: string | null;
  limite_acheteur_plafond: string | null;
  limite_acheteur_utilisee: string | null;
  historique_cycles_rembourses: number;
  grille_taux_total: string;
  grille_plafond_montant: string;
};

export function obtenirDossierDecision(avanceId: string, token: string) {
  return apiFetch<DossierDecisionOut>(`/avances/${avanceId}/dossier-decision`, { token });
}

export type DonneurOrdrePortefeuilleOut = {
  donneur_ordre_id: string;
  raison_sociale: string;
  encours: string;
  limite_plafond: string | null;
  limite_utilisee: string | null;
  retards: number;
};

export function obtenirPortefeuille(token: string) {
  return apiFetch<DonneurOrdrePortefeuilleOut[]>("/partenaire/portefeuille", { token });
}

export type PmeFinanceeOut = {
  pme_id: string;
  raison_sociale: string;
  ninea: string | null;
  encours: string;
  nombre_factures: number;
};

export type AcheteurPartenaireOut = {
  donneur_ordre_id: string;
  raison_sociale: string;
  secteur_activite: string | null;
  encours: string;
  taux_retard: string;
};

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

export function listerRemboursementsPartenaire(token: string) {
  return apiFetch<RemboursementSuperviseOut[]>("/partenaire/remboursements", { token });
}

export type NotificationPartenaireOut = {
  type: "opportunite" | "echeance" | "cheque" | "litige" | "remboursement" | "convention";
  titre: string;
  description: string;
  date: string;
  lu: boolean;
};

export function listerNotificationsPartenaire(token: string) {
  return apiFetch<NotificationPartenaireOut[]>("/partenaire/notifications", { token });
}

export type VolumeMoisOut = {
  mois: string;
  montant: string;
};

export type RapportResumeOut = {
  volume_par_mois: VolumeMoisOut[];
  montant_finance_ce_mois: string;
  variation_montant_finance_pct: string | null;
  frais_generes_ce_mois: string;
  variation_frais_generes_pct: string | null;
  rendement_portefeuille_pct: string;
};

export function obtenirRapportResume(token: string) {
  return apiFetch<RapportResumeOut>("/partenaire/rapports/resume", { token });
}

export async function telechargerRapport(periode: "mensuel" | "trimestriel" | "semestriel", token: string): Promise<void> {
  const response = await fetch(`${BASE_URL}/partenaire/rapports/telecharger?periode=${periode}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new ApiError(response.status, "Impossible de générer le rapport.");
  }
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `rapport-${periode}-${new Date().toISOString().slice(0, 10)}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
