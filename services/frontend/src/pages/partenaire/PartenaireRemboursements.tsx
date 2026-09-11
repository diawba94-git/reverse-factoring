import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { listerAvancesPartenaire, type RemboursementSuperviseOut } from "../../lib/partenaireApi";
import { listerFactures, type FactureOut } from "../../lib/facturesApi";
import { obtenirCheque, type ChequeGarantieOut } from "../../lib/chequeApi";
import type { AvanceOut } from "../../lib/pmeApi";
import { apiFetchPaginated } from "../../lib/apiClient";
import { Pagination } from "../../components/shell/Pagination";

const STATUT_BADGE: Record<string, { label: string; cls: string }> = {
  en_attente: { label: "En attente", cls: "pilote" },
  rapproche: { label: "Rapproché", cls: "avancee" },
  ecart_detecte: { label: "Écart détecté", cls: "litige" },
};

function fmt(v: string): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}

export function PartenaireRemboursements() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [remboursements, setRemboursements] = useState<RemboursementSuperviseOut[] | null>(null);
  const [avances, setAvances] = useState<AvanceOut[]>([]);
  const [factures, setFactures] = useState<FactureOut[]>([]);
  const [cheques, setCheques] = useState<Record<string, ChequeGarantieOut | null>>({});
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(25);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("per_page", String(perPage));
    apiFetchPaginated<RemboursementSuperviseOut>(`/partenaire/remboursements?${params.toString()}`, token)
      .then(({ items, total: t }) => {
        setRemboursements(items);
        setTotal(t);
      })
      .catch(() => setRemboursements([]));
  }, [token, page, perPage]);
  useEffect(() => {
    listerAvancesPartenaire({}, token).then(setAvances).catch(() => {});
    listerFactures({}, token).then(setFactures).catch(() => {});
  }, [token]);

  const avanceParId = useMemo(() => new Map(avances.map((a) => [a.id, a])), [avances]);
  const factureParId = useMemo(() => new Map(factures.map((f) => [f.id, f])), [factures]);

  useEffect(() => {
    if (!remboursements) return;
    remboursements.forEach((r) => {
      const avance = avanceParId.get(r.avance_id);
      const facture = avance ? factureParId.get(avance.facture_id) : undefined;
      if (!facture || facture.id in cheques) return;
      obtenirCheque(facture.id, token).then((c) => setCheques((prev) => ({ ...prev, [facture.id]: c })));
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remboursements, avanceParId, factureParId]);

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Remboursements</h1>
          <div className="sub">Paiements reçus et rapprochement</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        <div className="panel" style={{ padding: 0, overflow: "auto" }}>
          <table>
            <thead>
              <tr>
                <th style={{ padding: "12px 14px 10px" }}>Avance</th>
                <th>Donneur d'ordre</th>
                <th>Montant reçu</th>
                <th>Moyen</th>
                <th>Rapprochement</th>
              </tr>
            </thead>
            <tbody>
              {remboursements?.map((r) => {
                const avance = avanceParId.get(r.avance_id);
                const facture = avance ? factureParId.get(avance.facture_id) : undefined;
                const cheque = facture ? cheques[facture.id] : undefined;
                const moyen = cheque ? `Chèque n°${cheque.numero_cheque}` : "Virement";
                const badge = STATUT_BADGE[r.statut_rapprochement];
                return (
                  <tr key={r.id}>
                    <td className="mono ref" style={{ padding: "12px 14px" }}>
                      {facture?.numero_facture ?? r.avance_id.slice(0, 8)}
                    </td>
                    <td>{r.source_entreprise}</td>
                    <td className="mono">{fmt(r.montant_recu)}</td>
                    <td>{moyen}</td>
                    <td>
                      <span className={`status ${badge.cls}`}>{badge.label}</span>
                    </td>
                  </tr>
                );
              })}
              {remboursements && remboursements.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ padding: "20px 14px", textAlign: "center", color: "var(--muted)" }}>
                    Aucun remboursement pour le moment.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          <Pagination page={page} perPage={perPage} total={total} onPageChange={setPage} onPerPageChange={(n) => { setPerPage(n); setPage(1); }} />
        </div>
      </main>
    </>
  );
}
