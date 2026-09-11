import { useState, type FormEvent } from "react";
import { Modal } from "./Modal";
import { ErrorBanner } from "../auth/ErrorBanner";
import { ApiError, BASE_URL } from "../../lib/apiClient";
import type { EntrepriseOut } from "../../lib/adminApi";
import { FORME_JURIDIQUE_LABELS, TYPE_ENTREPRISE_LABELS } from "../../lib/roles";

export function RejeterKycModal({
  entreprise,
  onClose,
  onSubmit,
}: {
  entreprise: EntrepriseOut;
  onClose: () => void;
  onSubmit: (motif: string) => Promise<void>;
}) {
  const [motif, setMotif] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (motif.trim().length < 5) {
      setError("Précisez un motif (au moins 5 caractères) : il sera transmis à l'entreprise.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(motif.trim());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Une erreur est survenue. Réessayez.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal title="Rejeter le dossier KYC" subtitle={entreprise.raison_sociale} onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <div className="admin-field">
          <span className="admin-field-label">Motif du rejet (transmis à l'entreprise)</span>
          <textarea
            className="admin-select"
            style={{ minHeight: 80, resize: "vertical" }}
            value={motif}
            onChange={(e) => setMotif(e.target.value)}
          />
        </div>
        {error && <ErrorBanner message={error} />}
        <div className="admin-modal-actions">
          <button type="button" className="admin-button admin-button--secondary" onClick={onClose}>
            Annuler
          </button>
          <button type="submit" className="admin-button admin-button--danger" disabled={submitting}>
            {submitting ? "Rejet..." : "Confirmer le rejet"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export function DossierKycModal({
  entreprise,
  onClose,
  onValider,
  onRejeter,
}: {
  entreprise: EntrepriseOut;
  onClose: () => void;
  onValider: () => Promise<void>;
  onRejeter: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleValider() {
    setSubmitting(true);
    setError(null);
    try {
      await onValider();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Une erreur est survenue. Réessayez.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal title={entreprise.raison_sociale} subtitle="Dossier d'inscription" onClose={onClose}>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 13, marginBottom: 16 }}>
        <div>
          <strong>Type :</strong> {TYPE_ENTREPRISE_LABELS[entreprise.type]}
        </div>
        <div>
          <strong>Forme juridique :</strong>{" "}
          {entreprise.forme_juridique ? FORME_JURIDIQUE_LABELS[entreprise.forme_juridique] : "Non renseignée"}
        </div>
        <div>
          <strong>NINEA :</strong> {entreprise.ninea}
        </div>
        <div>
          <strong>RCCM :</strong> {entreprise.rccm ?? "Non fourni"}
        </div>
        <div>
          <strong>Secteur :</strong> {entreprise.secteur_activite}
        </div>
        <div>
          <strong>Contact :</strong> {entreprise.contact_telephone} · {entreprise.contact_email}
        </div>
        <div>
          <strong>Document KYC :</strong>{" "}
          {entreprise.kyc_document_url ? (
            <a href={`${BASE_URL}${entreprise.kyc_document_url}`} target="_blank" rel="noreferrer">
              Voir le document
            </a>
          ) : (
            "Aucun document téléversé"
          )}
        </div>
        {entreprise.motif_rejet_kyc && (
          <div>
            <strong>Motif du dernier rejet :</strong> {entreprise.motif_rejet_kyc}
          </div>
        )}
      </div>

      {error && <ErrorBanner message={error} />}

      <div className="admin-modal-actions">
        <button type="button" className="admin-button admin-button--danger" onClick={onRejeter}>
          Rejeter
        </button>
        <button type="button" className="admin-button admin-button--primary" onClick={handleValider} disabled={submitting}>
          {submitting ? "Validation..." : "Valider le KYC"}
        </button>
      </div>
    </Modal>
  );
}
