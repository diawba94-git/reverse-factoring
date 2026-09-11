import type { ShellNavItem } from "../components/shell/DashboardShell";

/** Les 8 items de la sidebar Acheteur de la maquette cedra-acheteur.html. */
export const ACHETEUR_NAV_ITEMS: Omit<ShellNavItem, "badge">[] = [
  { key: "dashboard", label: "Tableau de bord", icon: "i-grid", to: "/app/acheteur", end: true },
  { key: "factures", label: "Factures reçues", icon: "i-inbox", to: "/app/acheteur/factures" },
  { key: "validations", label: "Validations en attente", icon: "i-check-double", to: "/app/acheteur", end: true },
  { key: "historique", label: "Historique des validations", icon: "i-clock-history", to: "/app/acheteur/historique" },
  { key: "avoirs", label: "Avoirs à confirmer", icon: "i-return", to: "/app/acheteur/avoirs" },
  { key: "validateurs", label: "Validateurs de l'entreprise", icon: "i-users", to: "/app/acheteur/validateurs" },
  { key: "paiements", label: "Paiements à venir", icon: "i-wallet", to: "/app/acheteur/paiements" },
  { key: "notifications", label: "Notifications", icon: "i-bell", to: "/app/acheteur/notifications" },
  { key: "parametres", label: "Paramètres", icon: "i-settings", to: "/app/acheteur/parametres" },
];
