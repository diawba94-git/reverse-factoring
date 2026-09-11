import { apiFetch } from "./apiClient";

export type TypeEntreprise = "PME" | "GRANDE_ENTREPRISE" | "PARTENAIRE_FINANCIER";
export type StatutKyc = "en_attente" | "valide" | "rejete";
export type FormeJuridique = "personne_physique_entreprise_individuelle" | "gie" | "sarl" | "sa" | "autre";
export type RoleUtilisateur = "admin" | "membre_pme" | "validateur_1" | "validateur_2" | "agent_financier";

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type LoginResponse = {
  mfa_required: boolean;
  access_token: string | null;
  refresh_token: string | null;
  token_type: string;
};

export type MeEntreprise = {
  id: string;
  type: TypeEntreprise;
  raison_sociale: string;
  statut_kyc: StatutKyc;
  kyc_document_url: string | null;
  motif_rejet_kyc: string | null;
};

export type MeResponse = {
  id: string;
  telephone: string;
  email: string | null;
  nom: string | null;
  role: RoleUtilisateur;
  mfa_actif: boolean;
  entreprise: MeEntreprise;
};

export type RegisterEntreprisePayload = {
  type: TypeEntreprise;
  raison_sociale: string;
  ninea: string;
  forme_juridique: FormeJuridique;
  rccm?: string;
  secteur_activite: string;
  adresse: string;
  telephone: string;
  email: string;
  mot_de_passe: string;
};

export function registerEntreprise(payload: RegisterEntreprisePayload) {
  return apiFetch<TokenResponse>("/auth/register-entreprise", { method: "POST", body: payload });
}

export type LoginPayload = {
  /** Numero de telephone ou email du compte. */
  identifiant: string;
  mot_de_passe: string;
  code_mfa?: string;
};

export function login(payload: LoginPayload) {
  return apiFetch<LoginResponse>("/auth/login", { method: "POST", body: payload });
}

export function refreshTokens(refreshToken: string) {
  return apiFetch<TokenResponse>("/auth/refresh", { method: "POST", body: { refresh_token: refreshToken } });
}

export function me(accessToken: string) {
  return apiFetch<MeResponse>("/auth/me", { token: accessToken });
}

export function uploadKycDocument(entrepriseId: string, file: File, accessToken: string) {
  const formData = new FormData();
  formData.append("fichier", file);
  return apiFetch<{ kyc_document_url: string; statut_kyc: StatutKyc }>(`/entreprises/${entrepriseId}/kyc`, {
    method: "POST",
    body: formData,
    token: accessToken,
    isFormData: true,
  });
}
