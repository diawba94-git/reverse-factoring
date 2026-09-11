import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { type FactureOut } from "../../lib/facturesApi";
import { listerToutesAvances, type AvanceOut } from "../../lib/pmeApi";
import { apiFetch, apiFetchPaginated } from "../../lib/apiClient";
import { obtenirCheque, type ChequeGarantieOut } from "../../lib/chequeApi";
import { badgeStatutFacture } from "../../lib/statutFacture";
import { Pagination } from "../../components/shell/Pagination";

type EntrepriseLegere = { id: string; raison_sociale: string };

const STATUTS_FILTRE: { value: string; label: string }[] = [
  { value: "", label: "Tous les statuts" },
  { value: "en_attente_kyc_acheteur", label: "En attente KYC acheteur" },
  { value: "emise", label: "Émise" },
  { value: "validation_complementaire_requise", label: "Validation complémentaire requise" },
  { value: "validee", label: "Validée" },
  { value: "avance_demandee", label: "Avance demandée" },
  { value: "avance_versee", label: "Avancée (80%)" },
  { value: "soldee", label: "Soldée" },
  { value: "en_retard", label: "En retard" },
  { value: "litige", label: "Litige" },
];

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("fr-FR");
}

function formatMontant(value: string): string {
  return Number(value).toLocaleString("fr-FR");
}

export function AdminFactures() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [factures, setFactures] = useState<FactureOut[] | null>(null);
  const [donneurs, setDonneurs] = useState<EntrepriseLegere[]>([]);
  const [partenaires, setPartenaires] = useState<EntrepriseLegere[]>([]);
  const [avances, setAvances] = useState<AvanceOut[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [cheque, setCheque] = useState<ChequeGarantieOut | null>(null);

  const [recherche, setRecherche] = useState("");
  const [statutFiltre, setStatutFiltre] = useState("");
  const [donneurFiltre, setDonneurFiltre] = useState("");
  const [partenaireFiltre, setPartenaireFiltre] = useState("");
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(25);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    apiFetch<EntrepriseLegere[]>("/entreprises?type=GRANDE_ENTREPRISE", { token }).then(setDonneurs).catch(() => {});
    apiFetch<EntrepriseLegere[]>("/entreprises?type=PARTENAIRE_FINANCIER", { token }).then(setPartenaires).catch(() => {});
    listerToutesAvances({}, token).then(setAvances).catch(() => {});
  }, [token]);

  useEffect(() => {
    // La recherche (nom PME/acheteur) et le filtre partenaire n'ont pas d'equivalent
    // cote API (la facture n'a pas de lien direct vers le partenaire) : ils s'appliquent
    // en raffinement cote client sur la page chargee, le statut/l'acheteur sont eux de
    // vrais filtres serveur combines a la pagination.
    const params = new URLSearchParams();
    if (statutFiltre) params.set("statut", statutFiltre);
    if (donneurFiltre) params.set("donneur_ordre_id", donneurFiltre);
    params.set("page", String(page));
    params.set("per_page", String(perPage));
    apiFetchPaginated<FactureOut>(`/factures?${params.toString()}`, token)
      .then(({ items, total: t }) => {
        setFactures(items);
        setTotal(t);
        setSelectedId((prev) => (items.some((f) => f.id === prev) ? prev : items[0]?.id ?? null));
      })
      .catch(() => setFactures([]));
  }, [token, statutFiltre, donneurFiltre, page, perPage]);

  useEffect(() => {
    setPage(1);
  }, [statutFiltre, donneurFiltre]);

  useEffect(() => {
    if (!selectedId) return;
    setCheque(null);
    obtenirCheque(selectedId, token).then(setCheque).catch(() => setCheque(null));
  }, [selectedId, token]);

  const partenaireParFacture = useMemo(() => {
    const map = new Map<string, string>();
    avances.forEach((a) => map.set(a.facture_id, a.partenaire_financier_id));
    return map;
  }, [avances]);

  const donneurNom = useMemo(() => {
    const map = new Map(donneurs.map((d) => [d.id, d.raison_sociale]));
    return (id: string) => map.get(id) ?? "—";
  }, [donneurs]);

  const facturesFiltrees = useMemo(() => {
    if (!factures) return [];
    return factures.filter((f) => {
      if (recherche.trim()) {
        const q = recherche.trim().toLowerCase();
        const matchNumero = (f.numero_facture ?? "").toLowerCase().includes(q);
        const matchNoms = donneurNom(f.donneur_ordre_id).toLowerCase().includes(q);
        if (!matchNumero && !matchNoms) return false;
      }
      if (partenaireFiltre && partenaireParFacture.get(f.id) !== partenaireFiltre) return false;
      return true;
    });
  }, [factures, recherche, partenaireFiltre, donneurNom, partenaireParFacture]);

  const selected = factures?.find((f) => f.id === selectedId) ?? null;

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Factures</h1>
          <div className="sub">Toutes plateformes confondues — {factures?.length ?? "…"} factures</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        <div className="filters-bar">
          <input
            type="text"
            className="search-input"
            placeholder="Rechercher une référence, une PME, un acheteur..."
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
          <select className="select-filter" value={donneurFiltre} onChange={(e) => setDonneurFiltre(e.target.value)}>
            <option value="">Tous les acheteurs</option>
            {donneurs.map((d) => (
              <option key={d.id} value={d.id}>
                {d.raison_sociale}
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

        <div className="facture-master">
          <div className="panel" style={{ padding: 0, overflow: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th style={{ padding: "12px 14px 10px" }}>Référence</th>
                  <th>Acheteur</th>
                  <th>Montant</th>
                  <th>Mode</th>
                  <th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {facturesFiltrees.map((f) => {
                  const badge = badgeStatutFacture(f);
                  return (
                    <tr
                      key={f.id}
                      className={`fact-row ${selectedId === f.id ? "selected" : ""}`}
                      onClick={() => setSelectedId(f.id)}
                    >
                      <td className="mono ref" style={{ padding: "12px 14px" }}>
                        {f.numero_facture ?? "(brouillon)"}
                      </td>
                      <td>{donneurNom(f.donneur_ordre_id)}</td>
                      <td className="mono">{formatMontant(f.montant_ttc)}</td>
                      <td>
                        <span className="mode-tag">{f.source_creation === "native" ? "Native" : "Import"}</span>
                      </td>
                      <td>
                        <span className={`status ${badge.className}`}>{badge.label}</span>
                      </td>
                    </tr>
                  );
                })}
                {facturesFiltrees.length === 0 && (
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

          <div className="panel" id="facture-detail-panel">
            {!selected ? (
              <div className="empty-detail">Sélectionnez une facture dans la liste pour voir son détail.</div>
            ) : (
              <>
                <div className="detail-head">
                  <div>
                    <div className="ref mono">{selected.numero_facture ?? "(brouillon)"}</div>
                    <div className="title">
                      {/* La PME emettrice n'est pas dans FactureOut : on affiche l'acheteur, deja disponible. */}
                      → {donneurNom(selected.donneur_ordre_id)}
                    </div>
                  </div>
                  <div className="amt">
                    {formatMontant(selected.montant_ttc)}
                    <br />
                    <span style={{ fontSize: 10, color: "var(--muted)", fontWeight: 400 }}>{selected.devise} · TTC</span>
                  </div>
                </div>

                <div className="kv-grid">
                  <div className="kv">
                    <div className="l">Mode de création</div>
                    <div className="v">{selected.source_creation === "native" ? "Native" : "Import"} ({selected.lignes.length} lignes)</div>
                  </div>
                  <div className="kv">
                    <div className="l">Créée le</div>
                    <div className="v">{formatDate(selected.date_emission)}</div>
                  </div>
                  <div className="kv">
                    <div className="l">Montant HT</div>
                    <div className="v mono">{formatMontant(selected.montant_ht)}</div>
                  </div>
                  <div className="kv">
                    <div className="l">TVA ({Number(selected.taux_tva) * 100}%)</div>
                    <div className="v mono">{formatMontant(selected.montant_tva)}</div>
                  </div>
                  <div className="kv">
                    <div className="l">Échéance</div>
                    <div className="v">
                      {selected.duree_jours} jours — {formatDate(selected.date_echeance)}
                    </div>
                  </div>
                  <div className="kv">
                    <div className="l">Chèque de garantie</div>
                    <div className="v">
                      {cheque
                        ? cheque.statut === "rejete_sans_provision"
                          ? `✗ Rejeté (n°${cheque.numero_cheque})`
                          : `✓ ${cheque.statut === "declare" ? "Déclaré" : "Confirmé"} (n°${cheque.numero_cheque})`
                        : "—"}
                    </div>
                  </div>
                </div>

                <table className="lignes-table">
                  <thead>
                    <tr>
                      <th>Désignation</th>
                      <th>Qté</th>
                      <th>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selected.lignes.map((l) => (
                      <tr key={l.id}>
                        <td>{l.designation}</td>
                        <td>{l.quantite}</td>
                        <td className="mono">{formatMontant(l.montant_ligne)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <a className="doc-link" href={selected.piece_justificative_url} target="_blank" rel="noreferrer">
                  📄 Voir le PDF de la facture
                </a>

                <div className="mini-timeline">
                  <div className="mt-item">
                    <span className="mt-dot"></span> Facture émise <span className="time">{formatDate(selected.date_emission)}</span>
                  </div>
                  {selected.historique_validations.map((v, i) => (
                    <div className="mt-item" key={i}>
                      <span className="mt-dot"></span> Validation {i + 1}/2 ({v.nom ?? v.role_validateur})
                      <span className="time">{new Date(v.date_validation).toLocaleString("fr-FR")}</span>
                    </div>
                  ))}
                  {selected.historique_validations.length < 2 &&
                    ["validee", "avance_demandee", "avance_versee", "soldee"].includes(selected.statut) === false && (
                      <div className="mt-item">
                        <span className="mt-dot pending"></span> Validation {selected.historique_validations.length + 1}/2 en attente
                        <span className="time">—</span>
                      </div>
                    )}
                </div>
              </>
            )}
          </div>
        </div>
      </main>
    </>
  );
}
