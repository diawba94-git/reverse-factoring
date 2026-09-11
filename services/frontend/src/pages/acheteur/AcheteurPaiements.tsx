import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { listerFactures, type FactureOut } from "../../lib/facturesApi";
import { type AvanceOut } from "../../lib/pmeApi";
import { listerEntreprises } from "../../lib/adminApi";
import { apiFetchPaginated } from "../../lib/apiClient";
import { Pagination } from "../../components/shell/Pagination";

function fmt(v: string): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}
function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR");
}

export function AcheteurPaiements() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [factures, setFactures] = useState<FactureOut[] | null>(null);
  const [avances, setAvances] = useState<AvanceOut[]>([]);
  const [noms, setNoms] = useState<Record<string, string>>({});
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(25);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    const params = new URLSearchParams();
    params.set("statut", "avance_versee");
    params.set("tri", "echeance_asc");
    params.set("page", String(page));
    params.set("per_page", String(perPage));
    apiFetchPaginated<AvanceOut>(`/avances?${params.toString()}`, token)
      .then(({ items, total: t }) => {
        setAvances(items);
        setTotal(t);
      })
      .catch(() => setAvances([]));
  }, [token, page, perPage]);
  useEffect(() => {
    listerFactures({}, token).then(setFactures).catch(() => setFactures([]));
    listerEntreprises({}, token)
      .then((es) => {
        const map: Record<string, string> = {};
        es.forEach((e) => (map[e.id] = e.raison_sociale));
        setNoms(map);
      })
      .catch(() => {});
  }, [token]);

  const lignes = useMemo(() => {
    if (!factures) return [];
    const factureParId = new Map(factures.map((f) => [f.id, f]));
    return avances
      .map((a) => ({ avance: a, facture: factureParId.get(a.facture_id) }))
      .filter((l): l is { avance: AvanceOut; facture: FactureOut } => l.facture !== undefined)
      .sort((a, b) => a.facture.date_echeance.localeCompare(b.facture.date_echeance));
  }, [avances, factures]);

  const aujourdHui = new Date().toISOString().slice(0, 10);

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Paiements à venir</h1>
          <div className="sub">Échéances des factures que vous avez validées</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        <div className="panel" style={{ padding: 0, overflow: "auto" }}>
          <table>
            <thead>
              <tr>
                <th style={{ padding: "12px 14px 10px" }}>Référence</th>
                <th>Fournisseur</th>
                <th>Montant</th>
                <th>Échéance</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {lignes.map(({ avance, facture }) => {
                const enRetard = facture.date_echeance < aujourdHui;
                return (
                  <tr key={avance.id}>
                    <td className="mono" style={{ padding: "12px 14px" }}>
                      {facture.numero_facture ?? "(brouillon)"}
                    </td>
                    <td>{noms[facture.pme_id] ?? "…"}</td>
                    <td className="mono">{fmt(facture.montant_ttc)}</td>
                    <td>{fmtDate(facture.date_echeance)}</td>
                    <td>
                      <span className={`status ${enRetard ? "retard" : "validee"}`}>
                        {enRetard ? "Échéance dépassée" : "À payer au partenaire"}
                      </span>
                    </td>
                  </tr>
                );
              })}
              {lignes.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ padding: "20px 14px", textAlign: "center", color: "var(--muted)" }}>
                    Aucun paiement à venir pour le moment.
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
