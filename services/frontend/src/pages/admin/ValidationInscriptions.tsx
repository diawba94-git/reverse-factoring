import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { DossierKycModal, RejeterKycModal } from "../../components/admin/KycDossierModals";
import { ErrorBanner } from "../../components/auth/ErrorBanner";
import { listerEntreprises, mettreAJourStatutKyc, type EntrepriseOut } from "../../lib/adminApi";
import { TYPE_ENTREPRISE_LABELS } from "../../lib/roles";

const REGLES = [
  {
    titre: "NINEA obligatoire",
    detail: "Seul identifiant légal exigé à la création, quelle que soit la forme juridique de l'entreprise.",
  },
  {
    titre: "RCCM selon la forme juridique",
    detail:
      "Exigé pour valider le KYC d'un GIE, d'une SARL, d'une SA ou d'une entreprise « autre ». Jamais exigé pour une personne physique / entreprise individuelle.",
  },
  {
    titre: "Pièce d'identité obligatoire",
    detail: "Le dossier ne peut être validé tant qu'aucun document KYC n'a été téléversé par l'entreprise.",
  },
  {
    titre: "Rejet motivé",
    detail: "Le motif de rejet est obligatoire et transmis directement au demandeur.",
  },
];

export function ValidationInscriptions() {
  const { session } = useAuth();
  const token = session?.accessToken ?? "";

  const [entreprises, setEntreprises] = useState<EntrepriseOut[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [examen, setExamen] = useState<EntrepriseOut | null>(null);
  const [rejetEnCours, setRejetEnCours] = useState<EntrepriseOut | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  function recharger() {
    if (!token) return;
    setEntreprises(null);
    setLoadError(null);
    listerEntreprises({ statut_kyc: "en_attente" }, token)
      .then(setEntreprises)
      .catch(() => setLoadError("Impossible de charger les inscriptions en attente."));
  }

  useEffect(() => {
    recharger();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

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
    <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 18, alignItems: "start" }}>
      <div className="admin-panel">
        <div className="admin-panel-header">
          <div>
            <div className="admin-panel-title">Inscriptions à instruire</div>
            <div className="admin-panel-subtitle">
              PME fournisseurs, donneurs d'ordre et partenaires financiers en attente de décision.
            </div>
          </div>
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
          <div className="admin-empty-state">Aucune inscription en attente. Tout est à jour.</div>
        )}

        {entreprises !== null && entreprises.length > 0 && (
          <table className="admin-table">
            <thead>
              <tr>
                <th>Entreprise</th>
                <th>Rôle demandé</th>
                <th>Documents</th>
                <th>Déposée</th>
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
                  <td style={{ color: e.kyc_document_url ? "var(--color-success-text)" : "var(--color-error-text)" }}>
                    {e.kyc_document_url ? "Document fourni" : "Document manquant"}
                  </td>
                  <td>{e.date_creation ? new Date(e.date_creation).toLocaleDateString("fr-FR", { dateStyle: "medium" }) : "—"}</td>
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

      <div className="admin-panel">
        <div className="admin-panel-title">Règles d'instruction</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 16 }}>
          {REGLES.map((r) => (
            <div key={r.titre} style={{ borderBottom: "1px solid var(--color-divider)", paddingBottom: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 500 }}>{r.titre}</div>
              <div style={{ fontSize: 12, color: "var(--color-text-secondary)", lineHeight: 1.5, marginTop: 3 }}>
                {r.detail}
              </div>
            </div>
          ))}
        </div>
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
