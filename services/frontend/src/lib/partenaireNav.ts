import type { ShellNavItem } from "../components/shell/DashboardShell";

/** Les 10 items de la sidebar Partenaire de la maquette cedra-partenaire.html. */
export const PARTENAIRE_NAV_ITEMS: Omit<ShellNavItem, "badge">[] = [
  { key: "dashboard", label: "Tableau de bord", icon: "i-grid", to: "/app/partenaire", end: true },
  { key: "opportunites", label: "Opportunités", icon: "i-bell", to: "/app/partenaire/opportunites" },
  { key: "financements", label: "Financements", icon: "i-card", to: "/app/partenaire/financements" },
  { key: "portefeuille", label: "Portefeuille", icon: "i-folder", to: "/app/partenaire/portefeuille" },
  { key: "remboursements", label: "Remboursements", icon: "i-return", to: "/app/partenaire/remboursements" },
  { key: "avoirs", label: "Avoirs sur mon portefeuille", icon: "i-alert", to: "/app/partenaire/avoirs" },
  { key: "conventions", label: "Conventions & comptes dédiés", icon: "i-clipboard", to: "/app/partenaire/conventions" },
  { key: "pme", label: "PME partenaires", icon: "i-building", to: "/app/partenaire/pme" },
  { key: "acheteurs", label: "Acheteurs partenaires", icon: "i-cart", to: "/app/partenaire/acheteurs" },
  { key: "rapports", label: "Rapports", icon: "i-chart", to: "/app/partenaire/rapports" },
  { key: "grilles", label: "Grilles tarifaires", icon: "i-settings", to: "/app/partenaire/grilles" },
];
