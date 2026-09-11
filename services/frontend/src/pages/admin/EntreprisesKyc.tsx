import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { Badge } from "../../components/admin/Badge";
import { DossierKycModal, RejeterKycModal } from "../../components/admin/KycDossierModals";
import { ErrorBanner } from "../../components/auth/ErrorBanner";
import { listerEntreprises, mettreAJourStatutKyc, type EntrepriseOut } from "../../lib/adminApi";
import type { StatutKyc } from "../../lib/authApi";
import { STATUT_KYC_LABELS, TYPE_ENTREPRISE_LABELS } from "../../lib/roles";

const FILTRES: { label: string; value: StatutKyc | undefined }[] = [
  { label: "Toutes", value: undefined },
  { label: "En attente", value: "en_attente" },
  { label: "Validées", value: "valide" },
  { label: "Rejetées", value: "rejete" },
];

function statutBadgeTone(statut: StatutKyc) {
  if (statut === "valide") return "success" as const;
  if (statut === "rejete") return "danger" as const;
  return "warning" as const;
}

export function EntreprisesKyc() {
  const { session } = useAuth();
  const token = session?.accessToken ?? "";

  const [filtre, setFiltre] = useState<StatutKyc | undefined>(undefined);
  const [entreprises, setEntreprises] = useState<EntrepriseOut[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [examen, setExamen] = useState<EntrepriseOut | null>(null);
  const [rejetEnCours, setRejetEnCours] = useState<EntrepriseOut | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  function recharger() {
    if (!token) return;
    setEntreprises(null);
    setLoadError(null);
    listerEntreprises({ statut_kyc: filtre }, token)
      .then(setEntreprises)
      .catch(() => setLoadError("Impossible de charger les entreprises."));
  }

  useEffect(() => {
    recharger();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtre, token]);

  const compteurs = {
    total: entreprises?.length ?? null,
    valide: entreprises?.filter((e) => e.statut_kyc === "valide").length ?? null,
    en_attente: entreprises?.filter((e) => e.statut_kyc === "en_attente").length ?? null,
    rejete: entreprises?.filter((e) => e.statut_kyc === "rejete").length ?? null,
  };

  async function handleValider(entreprise: EntrepriseOut) {
    await mettreAJourStatutKyc(entreprise.id, { statut_kyc: "valide" }, token);
    setExamen(null);
    setSuccessMessage(`Dossier de ${entreprise.raison_sociale} validé.`);
    recharger();
  }

  async function handleRejeter(entreprise: EntrepriseOut, motif: string) {
    await mettreAJourStatutKyc(entreprise.id, { statut_kyc: "rejete", motif_rejet: motif }, token);
    setRejetEnCours(null);
    setExamen(null);
    setSuccessMessage(`Dossier de ${entreprise.raison_sociale} rejeté.`);
    recharger();
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <div style={{ display: "flex", gap: 14 }}>
        {[
          { label: "Entreprises inscrites", value: compteurs.total },
          { label: "KYC validés", value: compteurs.valide },
          { label: "En attente", value: compteurs.en_attente },
          { label: "Rejetés", value: compteurs.rejete },
        ].map((k) => (
          <div key={k.label} className="admin-panel" style={{ flex: 1 }}>
            <div style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: "0.07em", color: "var(--color-text-muted)", textTransform: "uppercase" }}>
              {k.label}
            </div>
            <div style={{ fontSize: 22, fontWeight: 600, marginTop: 9 }}>{k.value ?? "…"}</div>
          </div>
        ))}
      </div>

      <div className="admin-panel">
        <div className="admin-panel-header">
          <div>
            <div className="admin-panel-title">Entreprises et KYC</div>
            <div className="admin-panel-subtitle">Contrôle du NINEA, du RCCM et du dossier avant validation.</div>
          </div>
        </div>

        <div className="admin-filter-tabs">
          {FILTRES.map((f) => (
            <button
              key={f.label}
              type="button"
              className={`admin-filter-tab ${filtre === f.value ? "is-active" : ""}`}
              onClick={() => setFiltre(f.value)}
            >
              {f.label}
            </button>
          ))}
        </div>

        {successMessage && <div className="admin-success-banner">{successMessage}</div>}
        {loadError && <ErrorBanner message={loadError} />}
        {!loadError && entreprises === null && (
          <div className="admin-loading-state">
            <span className="admin-spinner" />
            Chargement...
          </div>
        )}
        {entreprises !== null && entreprises.length === 0 && (
          <div className="admin-empty-state">Aucune entreprise pour ce filtre.</div>
        )}

        {entreprises !== null && entreprises.length > 0 && (
          <table className="admin-table">
            <thead>
              <tr>
                <th>Entreprise</th>
                <th>Type</th>
                <th>Inscrite le</th>
                <th>Statut KYC</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {entreprises.map((e) => (
                <tr key={e.id}>
                  <td>
                    <div style={{ fontWeight: 500 }}>{e.raison_sociale}</div>
                    <div style={{ fontSize: 11.5, color: "var(--color-text-faint)" }}>NINEA {e.ninea}</div>
                  </td>
                  <td>{TYPE_ENTREPRISE_LABELS[e.type]}</td>
                  <td>{e.date_creation ? new Date(e.date_creation).toLocaleDateString("fr-FR", { dateStyle: "medium" }) : "—"}</td>
                  <td>
                    <Badge tone={statutBadgeTone(e.statut_kyc)}>{STATUT_KYC_LABELS[e.statut_kyc]}</Badge>
                  </td>
                  <td>
                    <div className="admin-table-actions">
                      <button
                        type="button"
                        className="admin-button admin-button--secondary admin-button--small"
                        onClick={() => setExamen(e)}
                      >
                        Examiner
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {examen && !rejetEnCours && (
        <DossierKycModal
          entreprise={examen}
          onClose={() => setExamen(null)}
          onValider={() => handleValider(examen)}
          onRejeter={() => setRejetEnCours(examen)}
        />
      )}

      {rejetEnCours && (
        <RejeterKycModal
          entreprise={rejetEnCours}
          onClose={() => setRejetEnCours(null)}
          onSubmit={(motif) => handleRejeter(rejetEnCours, motif)}
        />
      )}
    </div>
  );
}
