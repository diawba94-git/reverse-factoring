import type { FormeJuridique, RoleUtilisateur, StatutKyc, TypeEntreprise } from "./authApi";

/** Mirrors app.services.roles.ROLES_AUTORISES_PAR_TYPE on the backend. `admin` never
 * appears here on purpose: it is never attributable through this screen (see backend
 * app.routers.admin._verifier_role_autorise), only via a separate, Cedra-internal
 * mechanism. This frontend list is a UX convenience only — the backend re-validates the
 * same rule on every request regardless of what the UI lets the admin pick. */
export const ROLES_PAR_TYPE_ENTREPRISE: Record<TypeEntreprise, RoleUtilisateur[]> = {
  PME: ["membre_pme"],
  GRANDE_ENTREPRISE: ["validateur_1", "validateur_2"],
  PARTENAIRE_FINANCIER: ["agent_financier"],
};

export const ROLE_LABELS: Record<RoleUtilisateur, string> = {
  admin: "Administrateur",
  membre_pme: "Membre PME",
  validateur_1: "Validateur 1",
  validateur_2: "Validateur 2",
  agent_financier: "Agent financier",
};

export const TYPE_ENTREPRISE_LABELS: Record<TypeEntreprise, string> = {
  PME: "PME (fournisseur)",
  GRANDE_ENTREPRISE: "Donneur d'ordre",
  PARTENAIRE_FINANCIER: "Partenaire financier",
};

export const STATUT_KYC_LABELS: Record<StatutKyc, string> = {
  en_attente: "KYC en attente",
  valide: "KYC validé",
  rejete: "KYC rejeté",
};

export const PORTEE_FAQ_LABELS: Record<string, string> = {
  toutes: "Toutes les interfaces",
  pme: "PME fournisseur",
  donneur_ordre: "Donneur d'ordre",
  partenaire_financier: "Partenaire financier",
};

export const FORME_JURIDIQUE_LABELS: Record<FormeJuridique, string> = {
  personne_physique_entreprise_individuelle: "Personne physique / entreprise individuelle",
  gie: "GIE",
  sarl: "SARL",
  sa: "SA",
  autre: "Autre",
};
