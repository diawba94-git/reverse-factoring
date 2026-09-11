import { apiFetch } from "./apiClient";
import type { EntrepriseOut } from "./adminApi";
import type { FormeJuridique } from "./authApi";

export type FicheMinimalePayload = {
  raison_sociale: string;
  contact_invitation_nom: string;
  contact_invitation_email: string;
};

export type FicheMinimaleOut = EntrepriseOut & { token_invitation: string | null };

export function creerFicheMinimale(payload: FicheMinimalePayload, token: string) {
  return apiFetch<FicheMinimaleOut>("/entreprises/fiche-minimale", { method: "POST", body: payload, token });
}

export function obtenirEntreprise(id: string, token: string) {
  return apiFetch<EntrepriseOut>(`/entreprises/${id}`, { token });
}

export type EntrepriseUpdatePayload = {
  forme_juridique?: FormeJuridique;
  ninea?: string;
  rccm?: string | null;
  secteur_activite?: string;
  adresse?: string;
  contact_telephone?: string;
  contact_email?: string;
};

export function modifierEntreprise(id: string, payload: EntrepriseUpdatePayload, token: string) {
  return apiFetch<EntrepriseOut>(`/entreprises/${id}`, { method: "PUT", body: payload, token });
}

export type RejoindreEntreprisePayload = {
  nom: string;
  telephone: string;
  mot_de_passe: string;
};

export function rejoindreEntreprise(token: string, payload: RejoindreEntreprisePayload) {
  return apiFetch<{ access_token: string; refresh_token: string; token_type: string }>(
    `/auth/rejoindre-entreprise/${token}`,
    { method: "POST", body: payload },
  );
}
