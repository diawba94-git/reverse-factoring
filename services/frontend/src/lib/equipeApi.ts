import { apiFetch } from "./apiClient";
import type { UtilisateurOut } from "./adminApi";

export type SessionOut = {
  id: string;
  created_at: string;
  expires_at: string;
  revoked: boolean;
  user_agent: string | null;
  ip_address: string | null;
};

export function listerEquipeInterne(token: string) {
  return apiFetch<UtilisateurOut[]>("/utilisateurs?role=admin", { token });
}

export type CreerMembreEquipePayload = {
  entreprise_id: string;
  nom: string;
  telephone: string;
  email: string;
  mot_de_passe: string;
};

export function creerMembreEquipe(payload: CreerMembreEquipePayload, token: string) {
  return apiFetch<UtilisateurOut>("/utilisateurs", {
    method: "POST",
    body: { ...payload, role: "admin" },
    token,
  });
}

export function listerSessions(utilisateurId: string, token: string) {
  return apiFetch<SessionOut[]>(`/admin/utilisateurs/${utilisateurId}/sessions`, { token });
}

export function revoquerSession(sessionId: string, token: string) {
  return apiFetch<void>(`/admin/sessions/${sessionId}/revoquer`, { method: "POST", token });
}

export function revoquerToutesLesSessions(utilisateurId: string, token: string) {
  return apiFetch<void>(`/admin/utilisateurs/${utilisateurId}/sessions/revoquer-tout`, { method: "POST", token });
}
