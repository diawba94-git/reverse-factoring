import { apiFetch } from "./apiClient";

export type DashboardAdminOut = {
  nombre_entreprises: number;
  entreprises_par_type: Record<string, number>;
  entreprises_creees_ce_mois: Record<string, number>;
  evolution_entreprises_hebdo: Record<string, number[]>;
  evolution_volume_hebdo: string[];
  nombre_utilisateurs: number;
  nombre_factures: number;
  nombre_avances: number;
  montant_total_avance_verse: string;
  montant_total_avance_verse_delta_pourcentage: string | null;
  montant_total_frais_plateforme: string;
  repartition_volume: Record<string, string>;
  tickets_ouverts: number;
};

export function obtenirDashboardAdmin(token: string) {
  return apiFetch<DashboardAdminOut>("/dashboard/admin", { token });
}
