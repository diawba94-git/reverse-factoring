import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { type AvanceOut } from "../../lib/pmeApi";
import { listerFactures, type FactureOut } from "../../lib/facturesApi";
import { apiFetch, apiFetchPaginated } from "../../lib/apiClient";
import { Pagination } from "../../components/shell/Pagination";

type EntrepriseLegere = { id: string; raison_sociale: string };

const STATUTS_FILTRE: { value: string; label: string }[] = [
  { value: "", label: "Tous les statuts" },
  { value: "en_attente_validation", label: "En attente de décision" },
  { value: "avance_versee", label: "Avance versée" },
  { value: "soldee", label: "Soldée" },
  { value: "en_defaut", label: "En défaut" },
  { value: "rejetee", label: "Rejetée" },
];

const STATUT_BADGE: Record<string, { label: string; cls: string }> = {
  en_attente_validation: { label: "En attente", cls: "validation" },
  avance_versee: { label: "Avance versée", cls: "avancee" },
  soldee: { label: "Soldée", cls: "soldee" },
  en_defaut: { label: "En défaut", cls: "litige" },
  rejetee: { label: "Rejetée", cls: "litige" },
};

function formatMontant(value: string): string {
  return Number(value).toLocaleString("fr-FR");
}

export function AdminAvances() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [avances, setAvances] = useState<AvanceOut[] | null>(null);
  const [factures, setFactures] = useState<FactureOut[]>([]);
  const [pmes, setPmes] = useState<EntrepriseLegere[]>([]);
  const [partenaires, setPartenaires] = useState<EntrepriseLegere[]>([]);

  const [recherche, setRecherche] = useState("");
  const [statutFiltre, setStatutFiltre] = useState("");
  const [partenaireFiltre, setPartenaireFiltre] = useState("");
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(25);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    listerFactures({}, token).then(setFactures).catch(() => {});
    apiFetch<EntrepriseLegere[]>("/entreprises?type=PME", { token }).then(setPmes).catch(() => {});
    apiFetch<EntrepriseLegere[]>("/entreprises?type=PARTENAIRE_FINANCIER", { token }).then(setPartenaires).catch(() => {});
  }, [token]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (statutFiltre) params.set("statut", statutFiltre);
    if (partenaireFiltre) params.set("partenaire_financier_id", partenaireFiltre);
    params.set("page", String(page));
    params.set("per_page", String(perPage));
    apiFetchPaginated<AvanceOut>(`/avances?${params.toString()}`, token)
      .then(({ items, total: t }) => {
        setAvances(items);
        setTotal(t);
      })
      .catch(() => setAvances([]));
  }, [token, statutFiltre, partenaireFiltre, page, perPage]);

  useEffect(() => {
    setPage(1);
  }, [statutFiltre, partenaireFiltre]);

  const factureParId = useMemo(() => new Map(factures.map((f) => [f.id, f])), [factures]);
  const pmeNom = useMemo(() => {
    const map = new Map(pmes.map((p) => [p.id, p.raison_sociale]));
    return (id: string | undefined) => (id ? map.get(id) ?? "—" : "—");
  }, [pmes]);
  const partenaireNom = useMemo(() => {
    const map = new Map(partenaires.map((p) => [p.id, p.raison_sociale]));
    return (id: string) => map.get(id) ?? "—";
  }, [partenaires]);

  const avancesFiltrees = useMemo(() => {
    if (!avances) return [];
    return avances.filter((a) => {
      const facture = factureParId.get(a.facture_id);
      if (recherche.trim()) {
        const q = recherche.trim().toLowerCase();
        const matchRef = (facture?.numero_facture ?? "").toLowerCase().includes(q);
        const matchPme = pmeNom(facture?.pme_id).toLowerCase().includes(q);
        if (!matchRef && !matchPme) return false;
      }
      return true;
    });
  }, [avances, recherche, factureParId, pmeNom]);

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Avances</h1>
          <div className="sub">Toutes les avances demandées, tous partenaires confondus</div>
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
          <select className="select-filter" value={partenaireFiltre} onChange={(e) => setPartenaireFiltre(e.target.value)}>
            <option value="">Tous les partenaires</option>
            {partenaires.map((p) => (
              <option key={p.id} value={p.id}>
                {p.raison_sociale}
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
                <th>Partenaire</th>
                <th>Avance (80%)</th>
                <th>Solde attendu</th>
                <th>Garantie</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {avancesFiltrees.map((a) => {
                const facture = factureParId.get(a.facture_id);
                const badge = STATUT_BADGE[a.statut] ?? { label: a.statut, cls: "validation" };
                return (
                  <tr key={a.id}>
                    <td className="mono ref" style={{ padding: "12px 14px" }}>
                      {facture?.numero_facture ?? a.id.slice(0, 8)}
                    </td>
                    <td>{pmeNom(facture?.pme_id)}</td>
                    <td>{partenaireNom(a.partenaire_financier_id)}</td>
                    <td className="mono">{formatMontant(a.montant_avance_initial)}</td>
                    <td className="mono">{formatMontant(a.montant_solde_du)}</td>
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
              {avancesFiltrees.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ padding: "20px 14px", textAlign: "center", color: "var(--muted)" }}>
                    Aucune avance pour ces filtres.
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
