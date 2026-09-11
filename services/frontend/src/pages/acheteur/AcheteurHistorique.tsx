import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { type FactureOut } from "../../lib/facturesApi";
import { listerEntreprises } from "../../lib/adminApi";
import { apiFetchPaginated } from "../../lib/apiClient";
import { Pagination } from "../../components/shell/Pagination";

function fmt(v: string): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}
function fmtDateHeure(iso: string): string {
  const d = new Date(iso);
  return `${d.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" })} ${d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}`;
}

export function AcheteurHistorique() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [factures, setFactures] = useState<FactureOut[] | null>(null);
  const [noms, setNoms] = useState<Record<string, string>>({});
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(25);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    const params = new URLSearchParams();
    params.set("entierement_validee", "true");
    params.set("page", String(page));
    params.set("per_page", String(perPage));
    apiFetchPaginated<FactureOut>(`/factures?${params.toString()}`, token)
      .then(({ items, total: t }) => {
        setFactures(items);
        setTotal(t);
      })
      .catch(() => setFactures([]));
  }, [token, page, perPage]);
  useEffect(() => {
    listerEntreprises({}, token)
      .then((es) => {
        const map: Record<string, string> = {};
        es.forEach((e) => (map[e.id] = e.raison_sociale));
        setNoms(map);
      })
      .catch(() => {});
  }, [token]);

  const validees = factures ?? [];

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Historique des validations</h1>
          <div className="sub">Factures déjà validées, avec le détail des deux validateurs</div>
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
                <th>Validateur 1</th>
                <th>Validateur 2</th>
              </tr>
            </thead>
            <tbody>
              {validees.map((f) => {
                const [v1, v2] = f.historique_validations;
                return (
                  <tr key={f.id}>
                    <td className="mono" style={{ padding: "12px 14px" }}>
                      {f.numero_facture ?? "(brouillon)"}
                    </td>
                    <td>{noms[f.pme_id] ?? "…"}</td>
                    <td className="mono">{fmt(f.montant_ttc)}</td>
                    <td>
                      {v1.nom ?? "—"} — {fmtDateHeure(v1.date_validation)}
                    </td>
                    <td>
                      {v2.nom ?? "—"} — {fmtDateHeure(v2.date_validation)}
                    </td>
                  </tr>
                );
              })}
              {validees.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ padding: "20px 14px", textAlign: "center", color: "var(--muted)" }}>
                    Aucune facture entièrement validée pour le moment.
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
