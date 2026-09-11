import { BASE_URL, ApiError } from "./apiClient";

export type StatutChequeGarantie = "declare" | "confirme_par_donneur_ordre" | "remis_au_partenaire" | "encaisse" | "rejete_sans_provision";

export type ChequeGarantieOut = {
  id: string;
  facture_id: string;
  numero_cheque: string;
  banque_emettrice: string;
  date_encaissement_prevue: string;
  piece_jointe_url: string;
  statut: StatutChequeGarantie;
  date_remise_partenaire: string | null;
  date_creation: string;
};

export type DeclarerChequePayload = {
  numeroCheque: string;
  banqueEmettrice: string;
  dateEncaissementPrevue: string;
  fichier: File;
};

export async function declarerCheque(factureId: string, payload: DeclarerChequePayload, token: string): Promise<ChequeGarantieOut> {
  const params = new URLSearchParams({
    numero_cheque: payload.numeroCheque,
    banque_emettrice: payload.banqueEmettrice,
    date_encaissement_prevue: payload.dateEncaissementPrevue,
  });
  const form = new FormData();
  form.append("fichier", payload.fichier);

  const response = await fetch(`${BASE_URL}/factures/${factureId}/cheque?${params.toString()}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  const text = await response.text();
  const parsed = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail = parsed && typeof parsed === "object" && "detail" in parsed ? String(parsed.detail) : "Échec de la déclaration du chèque.";
    throw new ApiError(response.status, detail);
  }
  return parsed as ChequeGarantieOut;
}

export async function obtenirCheque(factureId: string, token: string): Promise<ChequeGarantieOut | null> {
  const response = await fetch(`${BASE_URL}/factures/${factureId}/cheque`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 404) return null;
  const text = await response.text();
  return text ? (JSON.parse(text) as ChequeGarantieOut) : null;
}
