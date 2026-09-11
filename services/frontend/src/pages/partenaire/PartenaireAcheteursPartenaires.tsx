import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import type { AcheteurPartenaireOut } from "../../lib/partenaireApi";
import { apiFetchPaginated } from "../../lib/apiClient";
import { Pagination } from "../../components/shell/Pagination";

function fmt(v: string): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}

export function PartenaireAcheteursPartenaires() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [lignes, setLignes] = useState<AcheteurPartenaireOut[] | null>(null);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(25);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("per_page", String(perPage));
    apiFetchPaginated<AcheteurPartenaireOut>(`/partenaire/acheteurs?${params.toString()}`, token)
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
          <h1>Acheteurs partenaires</h1>
          <div className="sub">{total || lignes?.length || "…"} acheteurs actifs sur votre portefeuille</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        <div className="panel" style={{ padding: 0, overflow: "auto" }}>
          <table>
            <thead>
              <tr>
                <th style={{ padding: "12px 14px 10px" }}>Acheteur</th>
                <th>Secteur</th>
                <th>Encours</th>
                <th>Taux de retard</th>
              </tr>
            </thead>
            <tbody>
              {lignes?.map((l) => (
                <tr key={l.donneur_ordre_id}>
                  <td style={{ padding: "12px 14px" }}>{l.raison_sociale}</td>
                  <td>{l.secteur_activite ?? "—"}</td>
                  <td className="mono">{fmt(l.encours)}</td>
                  <td>{l.taux_retard}%</td>
                </tr>
              ))}
              {lignes && lignes.length === 0 && (
                <tr>
                  <td colSpan={4} style={{ padding: "20px 14px", textAlign: "center", color: "var(--muted)" }}>
                    Aucun acheteur dans votre portefeuille pour le moment.
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
