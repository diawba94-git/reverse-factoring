import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { listerFactures, type FactureOut } from "../../lib/facturesApi";
import { listerEntreprises } from "../../lib/adminApi";
import type { AvanceOut } from "../../lib/pmeApi";
import { apiFetchPaginated } from "../../lib/apiClient";
import { Pagination } from "../../components/shell/Pagination";

const STATUTS_FILTRE: { value: string; label: string }[] = [
  { value: "", label: "Tous les statuts" },
  { value: "en_attente_validation", label: "En attente" },
  { value: "avance_versee", label: "Avance versée" },
  { value: "soldee", label: "Soldée" },
  { value: "en_defaut", label: "En défaut" },
  { value: "rejetee", label: "Rejetée" },
];

const STATUT_BADGE: Record<string, { label: string; cls: string }> = {
  en_attente_validation: { label: "En attente", cls: "pilote" },
  avance_versee: { label: "Avance versée", cls: "avancee" },
  soldee: { label: "Soldée", cls: "soldee" },
  en_defaut: { label: "En défaut", cls: "litige" },
  rejetee: { label: "Rejetée", cls: "litige" },
};

function fmt(v: string): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}

export function PartenaireFinancements() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [avances, setAvances] = useState<AvanceOut[] | null>(null);
  const [factures, setFactures] = useState<FactureOut[]>([]);
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
    apiFetchPaginated<AvanceOut>(`/avances?${params.toString()}`, token)
      .then(({ items, total: t }) => {
        setAvances(items);
        setTotal(t);
      })
      .catch(() => setAvances([]));
  }, [token, statutFiltre, page, perPage]);
  useEffect(() => {
    setPage(1);
  }, [statutFiltre]);
  useEffect(() => {
    listerFactures({}, token).then(setFactures).catch(() => {});
    listerEntreprises({}, token)
      .then((es) => {
        const map: Record<string, string> = {};
        es.forEach((e) => (map[e.id] = e.raison_sociale));
        setNoms(map);
      })
      .catch(() => {});
  }, [token]);

  const factureParId = useMemo(() => new Map(factures.map((f) => [f.id, f])), [factures]);

  const filtrees = useMemo(() => {
    if (!avances) return [];
    return avances.filter((a) => {
      const facture = factureParId.get(a.facture_id);
      if (recherche.trim()) {
        const q = recherche.trim().toLowerCase();
        const matchRef = (facture?.numero_facture ?? "").toLowerCase().includes(q);
        const matchPme = (noms[facture?.pme_id ?? ""] ?? "").toLowerCase().includes(q);
        if (!matchRef && !matchPme) return false;
      }
      return true;
    });
  }, [avances, recherche, factureParId, noms]);

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Financements</h1>
          <div className="sub">Toutes les avances de votre portefeuille</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        <div className="filters-bar">
          <input
            type="text"
            className="search-input"
            placeholder="Rechercher une référence, une PME..."
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
                <th>PME</th>
                <th>Acheteur</th>
                <th>Avance (80%)</th>
                <th>Garantie</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {filtrees.map((a) => {
                const facture = factureParId.get(a.facture_id);
                const badge = STATUT_BADGE[a.statut] ?? { label: a.statut, cls: "pilote" };
                return (
                  <tr key={a.id}>
                    <td className="mono ref" style={{ padding: "12px 14px" }}>
                      {facture?.numero_facture ?? a.id.slice(0, 8)}
                    </td>
                    <td>{noms[facture?.pme_id ?? ""] ?? "…"}</td>
                    <td>{noms[facture?.donneur_ordre_id ?? ""] ?? "…"}</td>
                    <td className="mono">{fmt(a.montant_avance_initial)}</td>
                    <td>
                      {a.garantie_detenue_avant_financement ? (
                        <span className="cheque-flag">🗹 Confirmé</span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>
                      <span className={`status ${badge.cls}`}>{badge.label}</span>
                    </td>
                  </tr>
                );
              })}
              {filtrees.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ padding: "20px 14px", textAlign: "center", color: "var(--muted)" }}>
                    Aucun financement pour ces filtres.
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
