import type { ShellNavItem } from "../components/shell/DashboardShell";

/** Les 8 items de la sidebar PME de la maquette cedra-pme.html. */
export const PME_NAV_ITEMS: Omit<ShellNavItem, "badge">[] = [
  { key: "dashboard", label: "Tableau de bord", icon: "i-grid", to: "/app/pme", end: true },
  { key: "factures", label: "Mes factures", icon: "i-file", to: "/app/pme/factures" },
  { key: "avoirs", label: "Avoirs & créances", icon: "i-return", to: "/app/pme/avoirs" },
  { key: "creer", label: "Créer une facture", icon: "i-plus", to: "/app/pme/creer" },
  { key: "avance", label: "Demander une avance", icon: "i-card", to: "/app/pme/avance" },
  { key: "suivi", label: "Suivi de mes demandes", icon: "i-clock", to: "/app/pme/suivi" },
  { key: "utilisateurs", label: "Utilisateurs de l'entreprise", icon: "i-users", to: "/app/pme/utilisateurs" },
  { key: "notifications", label: "Notifications", icon: "i-bell", to: "/app/pme/notifications" },
  { key: "parametres", label: "Paramètres", icon: "i-settings", to: "/app/pme/parametres" },
];
