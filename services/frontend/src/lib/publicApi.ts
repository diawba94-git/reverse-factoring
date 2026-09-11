import { apiFetch } from "./apiClient";

export type PublicStatsOut = {
  pme_actives: number;
  acheteurs_actifs: number;
  volume_finance_total: string;
};

export function obtenirStatsPubliques() {
  return apiFetch<PublicStatsOut>("/public/stats");
}
