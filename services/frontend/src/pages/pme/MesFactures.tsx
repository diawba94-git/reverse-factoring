import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { usePme } from "../../context/PmeContext";
import { Modal } from "../../components/admin/Modal";
import { ErrorBanner } from "../../components/auth/ErrorBanner";
import { ApiError, apiFetch, apiFetchPaginated, BASE_URL } from "../../lib/apiClient";
import { listerDonneursOrdre, supprimerFacture, transmettreFacture, type DonneurOrdreOut, type FactureOut } from "../../lib/facturesApi";
import { obtenirCheque, type ChequeGarantieOut } from "../../lib/chequeApi";
import { badgeStatutFacture } from "../../lib/statutFacture";
import { Pagination } from "../../components/shell/Pagination";

const STATUTS_FILTRE: { value: string; label: string }[] = [
  { value: "", label: "Tous les statuts" },
  { value: "en_attente_kyc_acheteur", label: "En attente KYC acheteur" },
  { value: "emise", label: "Émise" },
  { value: "validation_complementaire_requise", label: "1/2 validations" },
  { value: "validee", label: "Validée" },
  { value: "avance_versee", label: "Avancée (80%)" },
  { value: "soldee", label: "Soldée" },
  { value: "en_retard", label: "En retard" },
  { value: "litige", label: "Litige" },
];

function fmt(v: string): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}
function fmtDateCourte(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR");
}

type ImportRapport = {
  total_lignes: number;
  succes: number;
  echecs: number;
  details: { ligne: number; succes: boolean; erreur?: string | null; conforme?: boolean | null }[];
};

function ResoumettreModal({
  facture,
  token,
  onClose,
  onDone,
}: {
  facture: FactureOut;
  token: string;
  onClose: () => void;
  onDone: () => void;
}) {
  const [fichier, setFichier] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    if (!fichier) {
      setError("Sélectionnez un fichier PDF.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("fichier", fichier);
      await apiFetch(`/factures/${facture.id}/resoumettre`, { method: "POST", body: form, isFormData: true, token });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Une erreur est survenue. Réessayez.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal title="Resoumettre la facture" subtitle={facture.numero_facture ?? undefined} onClose={onClose}>
      {facture.motifs_rejet_conformite && (
        <div style={{ marginBottom: 12, fontSize: 12.5, color: "var(--red)" }}>
          <strong>Motifs du rejet :</strong>
          <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
            {facture.motifs_rejet_conformite.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </div>
      )}
      <input type="file" accept="application/pdf" onChange={(e) => setFichier(e.target.files?.[0] ?? null)} />
      {error && <ErrorBanner message={error} />}
      <div className="admin-modal-actions">
        <button type="button" className="btn-secondary" onClick={onClose}>
          Annuler
        </button>
        <button type="button" className="btn-primary" disabled={submitting} onClick={handleSubmit}>
          {submitting ? "Envoi..." : "Resoumettre"}
        </button>
      </div>
    </Modal>
  );
}

export function MesFactures() {
  const { session } = useAuth();
  const { pmeId } = usePme();
  const token = session?.accessToken ?? "";

  const [donneurs, setDonneurs] = useState<DonneurOrdreOut[] | null>(null);
  const [factures, setFactures] = useState<FactureOut[] | null>(null);
  const [cheques, setCheques] = useState<Record<string, ChequeGarantieOut | null>>({});
  const [error, setError] = useState<string | null>(null);

  const [recherche, setRecherche] = useState("");
  const [statutFiltre, setStatutFiltre] = useState("");
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(25);
  const [total, setTotal] = useState(0);

  const [resoumettreCible, setResoumettreCible] = useState<FactureOut | null>(null);
  const [supprimerCible, setSupprimerCible] = useState<FactureOut | null>(null);
  const [transmissionEnCours, setTransmissionEnCours] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [importRapport, setImportRapport] = useState<ImportRapport | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function recharger() {
    if (!pmeId || !token) return;
    setFactures(null);
    setError(null);
    const params = new URLSearchParams();
    params.set("pme_id", pmeId);
    if (statutFiltre) params.set("statut", statutFiltre);
    params.set("page", String(page));
    params.set("per_page", String(perPage));
    apiFetchPaginated<FactureOut>(`/factures?${params.toString()}`, token)
      .then(({ items, total: t }) => {
        setFactures(items);
        setTotal(t);
      })
      .catch(() => setError("Impossible de charger les factures."));
  }

  useEffect(recharger, [pmeId, token, statutFiltre, page, perPage]);
  useEffect(() => {
    setPage(1);
  }, [statutFiltre]);
  useEffect(() => {
    if (!token) return;
    listerDonneursOrdre(token).then(setDonneurs).catch(() => undefined);
  }, [token]);

  useEffect(() => {
    if (!factures) return;
    factures.forEach((f) => {
      if (f.id in cheques) return;
      obtenirCheque(f.id, token).then((c) => setCheques((prev) => ({ ...prev, [f.id]: c })));
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [factures]);

  const facturesFiltrees = factures?.filter((f) => {
    if (!recherche.trim()) return true;
    const q = recherche.trim().toLowerCase();
    const matchRef = (f.numero_facture ?? "").toLowerCase().includes(q);
    const matchAcheteur = nomDonneur(f.donneur_ordre_id).toLowerCase().includes(q);
    return matchRef || matchAcheteur;
  });

  function nomDonneur(id: string): string {
    return donneurs?.find((d) => d.id === id)?.raison_sociale ?? "…";
  }

  async function handleTransmettre(f: FactureOut) {
    setActionError(null);
    setTransmissionEnCours(f.id);
    try {
      await transmettreFacture(f.id, token);
      recharger();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Transmission impossible.");
    } finally {
      setTransmissionEnCours(null);
    }
  }

  async function handleSupprimer() {
    if (!supprimerCible) return;
    setActionError(null);
    try {
      await supprimerFacture(supprimerCible.id, token);
      setSupprimerCible(null);
      recharger();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Suppression impossible.");
    }
  }

  async function handleImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const fichier = e.target.files?.[0];
    if (!fichier || !pmeId) return;
    setImportError(null);
    try {
      const form = new FormData();
      form.append("fichier", fichier);
      form.append("pme_id", pmeId);
      const rapport = await apiFetch<ImportRapport>("/factures/import", {
        method: "POST",
        body: form,
        isFormData: true,
        token,
      });
      setImportRapport(rapport);
      recharger();
    } catch (err) {
      setImportError(err instanceof ApiError ? err.message : "Import impossible.");
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Mes factures</h1>
          <div className="sub">{total || factures?.length || "…"} factures — toutes activités</div>
        </div>
        <div className="topbar-right">
          <input type="file" ref={fileInputRef} style={{ display: "none" }} accept=".csv,.xlsx,.xls" onChange={handleImportFile} />
          <button type="button" className="btn-secondary" onClick={() => fileInputRef.current?.click()}>
            Importer un fichier
          </button>
          <Link to="/app/pme/creer" className="btn-primary" style={{ textDecoration: "none" }}>
            Créer une facture
          </Link>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        {importError && <ErrorBanner message={importError} />}
        {actionError && <ErrorBanner message={actionError} />}
        {importRapport && (
          <div className="lit-detail" style={{ marginBottom: 14 }}>
            Import terminé : {importRapport.succes} facture(s) créée(s), {importRapport.echecs} échec(s) sur{" "}
            {importRapport.total_lignes} ligne(s).
          </div>
        )}
        <div className="filters-bar">
          <input
            type="text"
            className="search-input"
            placeholder="Rechercher une référence, un acheteur..."
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
        {error && <ErrorBanner message={error} />}
        <div className="panel" style={{ padding: 0, overflow: "auto" }}>
          <table>
            <thead>
              <tr>
                <th style={{ padding: "12px 14px 10px" }}>Référence</th>
                <th>Acheteur</th>
                <th>Montant</th>
                <th>Créée le</th>
                <th>Garantie</th>
                <th>Statut</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {facturesFiltrees?.map((f) => {
                const badge = badgeStatutFacture(f);
                const cheque = cheques[f.id];
                return (
                  <tr key={f.id}>
                    <td className="mono" style={{ padding: "12px 14px" }}>
                      {f.numero_facture ?? "(brouillon)"}
                    </td>
                    <td>{nomDonneur(f.donneur_ordre_id)}</td>
                    <td className="mono">{fmt(f.montant_ttc)}</td>
                    <td>{fmtDateCourte(f.date_emission)}</td>
                    <td>
                      {cheque?.statut === "confirme_par_donneur_ordre" ? (
                        <span className="cheque-flag">🗹 Confirmé</span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>
                      <span className={`status ${badge.className}`}>{badge.label}</span>
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                        {f.piece_justificative_url && (
                          <a className="btn-secondary" style={{ textDecoration: "none" }} href={`${BASE_URL}${f.piece_justificative_url}`} target="_blank" rel="noreferrer">
                            Voir le PDF
                          </a>
                        )}
                        {f.statut === "brouillon" && (
                          <>
                            <Link to={`/app/pme/creer?facture=${f.id}`} className="btn-secondary" style={{ textDecoration: "none" }}>
                              Modifier
                            </Link>
                            <button
                              type="button"
                              className="btn-primary"
                              disabled={transmissionEnCours === f.id}
                              onClick={() => handleTransmettre(f)}
                            >
                              {transmissionEnCours === f.id ? "Transmission..." : "Transmettre"}
                            </button>
                            <button type="button" className="btn-secondary" onClick={() => setSupprimerCible(f)}>
                              Supprimer
                            </button>
                          </>
                        )}
                        {f.statut === "rejetee_conformite" && (
                          <button type="button" className="btn-secondary" onClick={() => setResoumettreCible(f)}>
                            Resoumettre
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {facturesFiltrees && facturesFiltrees.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ padding: "20px 14px", textAlign: "center", color: "var(--muted)" }}>
                    Aucune facture pour ces filtres.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          <Pagination page={page} perPage={perPage} total={total} onPageChange={setPage} onPerPageChange={(n) => { setPerPage(n); setPage(1); }} />
        </div>
      </main>

      {resoumettreCible && (
        <ResoumettreModal
          facture={resoumettreCible}
          token={token}
          onClose={() => setResoumettreCible(null)}
          onDone={() => {
            setResoumettreCible(null);
            recharger();
          }}
        />
      )}

      {supprimerCible && (
        <Modal
          title="Supprimer ce brouillon ?"
          subtitle="Cette facture n'a jamais été transmise au donneur d'ordre : la suppression est définitive."
          onClose={() => setSupprimerCible(null)}
        >
          <div className="admin-modal-actions">
            <button type="button" className="btn-secondary" onClick={() => setSupprimerCible(null)}>
              Annuler
            </button>
            <button type="button" className="btn-primary" style={{ background: "var(--red)" }} onClick={handleSupprimer}>
              Supprimer définitivement
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
