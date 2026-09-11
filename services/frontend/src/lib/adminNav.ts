import type { ShellNavItem } from "../components/shell/DashboardShell";

/** Les 11 items de la sidebar admin de la maquette cedra-admin.html. */
export const ADMIN_NAV_ITEMS: Omit<ShellNavItem, "badge">[] = [
  { key: "dashboard", label: "Tableau de bord", icon: "i-grid", to: "/app/admin", end: true },
  { key: "factures", label: "Factures", icon: "i-file", to: "/app/admin/factures" },
  { key: "avances", label: "Avances", icon: "i-card", to: "/app/admin/avances" },
  { key: "remboursements", label: "Remboursements", icon: "i-return", to: "/app/admin/remboursements" },
  { key: "avoirs", label: "Avoirs & créances", icon: "i-alert", to: "/app/admin/avoirs" },
  { key: "conventions", label: "Conventions", icon: "i-clipboard", to: "/app/admin/conventions" },
  { key: "doublons", label: "Fusion des doublons", icon: "i-merge", to: "/app/admin/doublons" },
  { key: "litiges", label: "Litiges", icon: "i-alert", to: "/app/admin/litiges" },
  { key: "notifications", label: "Notifications", icon: "i-bell", to: "/app/admin/notifications" },
  { key: "rapports", label: "Rapports", icon: "i-chart", to: "/app/admin/rapports" },
  { key: "utilisateurs", label: "Utilisateurs & rôles", icon: "i-users", to: "/app/admin/utilisateurs" },
  { key: "grilles", label: "Grilles & paramètres", icon: "i-settings", to: "/app/admin/grilles" },
];

/** Ecrans admin existants sans emplacement dans la sidebar de la maquette (§ decision
 * produit : rester fidele au visuel des 11 items ci-dessus plutot que d'en ajouter).
 * Restent accessibles par URL directe, montes sous le meme AppShell. */
export const ADMIN_HIDDEN_ROUTES = [
  { key: "pilotage", path: "pilotage-legacy", label: "Pilotage" },
  { key: "kyc", path: "kyc-legacy", label: "Entreprises et KYC" },
  { key: "inscriptions", path: "inscriptions-legacy", label: "Validation des inscriptions" },
  { key: "equipe", path: "equipe-legacy", label: "Équipe Cedra" },
  { key: "logs", path: "logs-legacy", label: "Logs techniques" },
  { key: "faq", path: "faq-legacy", label: "FAQ" },
  { key: "parametres", path: "parametres-legacy", label: "Paramètres" },
];
