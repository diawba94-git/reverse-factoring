import { apiFetch } from "./apiClient";

export type RapportPeriodeOut = {
  periode: string;
  debut: string;
  fin: string;
  nombre_factures: number;
  montant_total_factures: string;
  nombre_avances: number;
  montant_total_avance_verse: string;
  montant_total_frais_plateforme: string;
  montant_total_rembourse: string;
};

export function obtenirRapport(periode: "mois" | "trimestre", token: string) {
  return apiFetch<RapportPeriodeOut>(`/admin/rapports?periode=${periode}`, { token });
}
