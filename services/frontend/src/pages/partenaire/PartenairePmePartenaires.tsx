import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import type { PmeFinanceeOut } from "../../lib/partenaireApi";
import { apiFetchPaginated } from "../../lib/apiClient";
import { Pagination } from "../../components/shell/Pagination";

function fmt(v: string): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}

export function PartenairePmePartenaires() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [lignes, setLignes] = useState<PmeFinanceeOut[] | null>(null);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(25);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("per_page", String(perPage));
    apiFetchPaginated<PmeFinanceeOut>(`/partenaire/pme-financees?${params.toString()}`, token)
      .then(({ items, total: t }) => {
        setLignes(items);
        setTotal(t);
      })
      .catch(() => setLignes([]));
  }, [token, page, perPage]);

  return (
    <>
      <header className="topbar">
        <div>
          <h1>PME partenaires</h1>
          <div className="sub">{total || lignes?.length || "…"} PME financées</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        <div className="panel" style={{ padding: 0, overflow: "auto" }}>
          <table>
            <thead>
              <tr>
                <th style={{ padding: "12px 14px 10px" }}>PME</th>
                <th>NINEA</th>
                <th>Encours</th>
                <th>Factures financées</th>
              </tr>
            </thead>
            <tbody>
              {lignes?.map((l) => (
                <tr key={l.pme_id}>
                  <td style={{ padding: "12px 14px" }}>{l.raison_sociale}</td>
                  <td className="mono">{l.ninea ?? "—"}</td>
                  <td className="mono">{fmt(l.encours)}</td>
                  <td>{l.nombre_factures}</td>
                </tr>
              ))}
              {lignes && lignes.length === 0 && (
                <tr>
                  <td colSpan={4} style={{ padding: "20px 14px", textAlign: "center", color: "var(--muted)" }}>
                    Aucune PME financée pour le moment.
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
