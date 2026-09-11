import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { type FactureOut } from "../../lib/facturesApi";
import { listerEntreprises } from "../../lib/adminApi";
import { badgeStatutFacture } from "../../lib/statutFacture";
import { apiFetchPaginated } from "../../lib/apiClient";
import { Pagination } from "../../components/shell/Pagination";

const STATUTS_FILTRE: { value: string; label: string }[] = [
  { value: "", label: "Tous les statuts" },
  { value: "emise", label: "0/2 validations" },
  { value: "validation_complementaire_requise", label: "1/2 validations" },
  { value: "validee", label: "Validée" },
  { value: "avance_versee", label: "Avancée" },
  { value: "soldee", label: "Soldée" },
];

function fmt(v: string): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}
function fmtDateCourte(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" });
}

export function AcheteurFacturesRecues() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [factures, setFactures] = useState<FactureOut[] | null>(null);
  const [noms, setNoms] = useState<Record<string, string>>({});
  const [recherche, setRecherche] = useState("");
  const [statutFiltre, setStatutFiltre] = useState("");
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(25);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    const params = new URLSearchParams();
    if (statutFiltre) params.set("statut", statutFiltre);
    params.set("page", String(page));
    params.set("per_page", String(perPage));
    apiFetchPaginated<FactureOut>(`/factures?${params.toString()}`, token)
      .then(({ items, total: t }) => {
        setFactures(items);
        setTotal(t);
      })
      .catch(() => setFactures([]));
  }, [token, statutFiltre, page, perPage]);
  useEffect(() => {
    setPage(1);
  }, [statutFiltre]);
  useEffect(() => {
    listerEntreprises({}, token)
      .then((es) => {
        const map: Record<string, string> = {};
        es.forEach((e) => (map[e.id] = e.raison_sociale));
        setNoms(map);
      })
      .catch(() => {});
  }, [token]);

  const filtrees = useMemo(() => {
    if (!factures) return [];
    return factures.filter((f) => {
      if (recherche.trim()) {
        const q = recherche.trim().toLowerCase();
        const matchRef = (f.numero_facture ?? "").toLowerCase().includes(q);
        const matchFournisseur = (noms[f.pme_id] ?? "").toLowerCase().includes(q);
        if (!matchRef && !matchFournisseur) return false;
      }
      return true;
    });
  }, [factures, recherche, noms]);

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Factures reçues</h1>
          <div className="sub">{total || factures?.length || "…"} factures — toutes provenances</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        <div className="filters-bar">
          <input
            type="text"
            className="search-input"
            placeholder="Rechercher une référence, un fournisseur..."
            value={recherche}
            onChange={(e) => setRecherche(e.target.value)}
          />
          <select className="select-filter" value={statutFiltre} onChange={(e) => setStatutFiltre(e.target.value)}>
            {STATUTS_FILTRE.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
        <div className="panel" style={{ padding: 0, overflow: "auto" }}>
          <table>
            <thead>
              <tr>
                <th style={{ padding: "12px 14px 10px" }}>Référence</th>
                <th>Fournisseur</th>
                <th>Montant</th>
                <th>Reçue le</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {filtrees.map((f) => {
                const badge = badgeStatutFacture(f);
                return (
                  <tr key={f.id}>
                    <td className="mono" style={{ padding: "12px 14px" }}>
                      {f.numero_facture ?? "(brouillon)"}
                    </td>
                    <td>{noms[f.pme_id] ?? "…"}</td>
                    <td className="mono">{fmt(f.montant_ttc)}</td>
                    <td>{fmtDateCourte(f.date_emission)}</td>
                    <td>
                      <span className={`status ${badge.className}`}>{badge.label}</span>
                    </td>
                  </tr>
                );
              })}
              {filtrees.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ padding: "20px 14px", textAlign: "center", color: "var(--muted)" }}>
                    Aucune facture pour ces filtres.
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
