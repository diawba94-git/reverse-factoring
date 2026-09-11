import { apiFetch } from "./apiClient";
import type { FormeJuridique, RoleUtilisateur, StatutKyc, TypeEntreprise } from "./authApi";

export type EntrepriseOut = {
  id: string;
  type: TypeEntreprise;
  raison_sociale: string;
  ninea: string | null;
  forme_juridique: FormeJuridique | null;
  rccm: string | null;
  statut_kyc: StatutKyc;
  secteur_activite: string | null;
  date_creation: string | null;
  contact_telephone: string | null;
  contact_email: string | null;
  adresse: string | null;
  kyc_document_url: string | null;
  motif_rejet_kyc: string | null;
  statut_fiche: "pre_inscrite" | "active";
  cree_par_entreprise_id: string | null;
  contact_invitation_nom: string | null;
  contact_invitation_email: string | null;
  date_invitation_envoyee: string | null;
  actif: boolean;
  created_at: string;
};

export type UtilisateurOut = {
  id: string;
  entreprise_id: string;
  role: RoleUtilisateur;
  nom: string | null;
  telephone: string;
  email: string | null;
  compte_actif: boolean;
  derniere_connexion: string | null;
};

export type UtilisateurCreeOut = UtilisateurOut & {
  mot_de_passe_temporaire: string;
};

export function listerEntreprises(
  filtres: { type?: TypeEntreprise; statut_kyc?: StatutKyc },
  token: string,
) {
  const params = new URLSearchParams();
  if (filtres.type) params.set("type", filtres.type);
  if (filtres.statut_kyc) params.set("statut_kyc", filtres.statut_kyc);
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<EntrepriseOut[]>(`/entreprises${query}`, { token });
}

export function listerUtilisateursEntreprise(entrepriseId: string, token: string) {
  return apiFetch<UtilisateurOut[]>(`/utilisateurs?entreprise_id=${encodeURIComponent(entrepriseId)}`, { token });
}

export type CreerUtilisateurPayload = {
  nom: string;
  telephone: string;
  email: string;
  role: RoleUtilisateur;
};

export function creerUtilisateurAdmin(entrepriseId: string, payload: CreerUtilisateurPayload, token: string) {
  return apiFetch<UtilisateurCreeOut>(`/admin/entreprises/${entrepriseId}/utilisateurs`, {
    method: "POST",
    body: payload,
    token,
  });
}

export type ModifierUtilisateurPayload = {
  role?: RoleUtilisateur;
  compte_actif?: boolean;
};

export function modifierUtilisateurAdmin(utilisateurId: string, payload: ModifierUtilisateurPayload, token: string) {
  return apiFetch<UtilisateurOut>(`/admin/utilisateurs/${utilisateurId}`, {
    method: "PATCH",
    body: payload,
    token,
  });
}

export type MettreAJourKycPayload = {
  statut_kyc: "valide" | "rejete";
  motif_rejet?: string;
};

export function mettreAJourStatutKyc(entrepriseId: string, payload: MettreAJourKycPayload, token: string) {
  return apiFetch<EntrepriseOut>(`/entreprises/${entrepriseId}/kyc`, {
    method: "PATCH",
    body: payload,
    token,
  });
}
