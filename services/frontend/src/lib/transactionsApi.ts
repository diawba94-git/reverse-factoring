import { apiFetch } from "./apiClient";

export type TransactionOut = {
  facture_id: string;
  numero_facture: string;
  fournisseur: string;
  acheteur: string;
  montant: string;
  etape: string;
  avance_id: string | null;
};

export function listerTransactions(token: string) {
  return apiFetch<TransactionOut[]>("/admin/transactions", { token });
}
