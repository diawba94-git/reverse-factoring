import type { FactureOut } from "./facturesApi";

/** Mappe un statut reel de facture vers le badge visuel des maquettes (classes .status.*
 * definies dans les feuilles de style des dashboards). Les statuts sans equivalent direct
 * dans les maquettes (brouillon, rejetee...) reutilisent la teinte la plus proche
 * semantiquement plutot que d'inventer une nouvelle couleur. */
export function badgeStatutFacture(facture: Pick<FactureOut, "statut" | "premiere_validation">): {
  label: string;
  className: string;
} {
  switch (facture.statut) {
    case "brouillon":
      return { label: "Brouillon", className: "brouillon" };
    case "en_attente_kyc_acheteur":
      return { label: "En attente KYC acheteur", className: "brouillon" };
    case "emise":
      return { label: facture.premiere_validation ? "1/2 validations" : "0/2 validations", className: "validation" };
    case "validation_complementaire_requise":
      return { label: "1/2 validations", className: "validation" };
    case "validee":
      return { label: "Validée", className: "validee" };
    case "avance_demandee":
      return { label: "Avance demandée", className: "validee" };
    case "avance_versee":
      return { label: "Avancée (80%)", className: "avancee" };
    case "soldee":
      return { label: "Soldée", className: "soldee" };
    case "en_retard":
      return { label: "En retard", className: "retard" };
    case "litige":
      return { label: "Litige", className: "litige" };
    case "rejetee":
      return { label: "Rejetée", className: "litige" };
    case "rejetee_conformite":
      return { label: "Rejetée (conformité)", className: "litige" };
    default:
      return { label: facture.statut, className: "validation" };
  }
}
