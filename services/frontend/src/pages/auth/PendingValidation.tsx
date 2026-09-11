import { useRef, useState, type ChangeEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { AuthLayout } from "./AuthLayout";
import { ErrorBanner } from "../../components/auth/ErrorBanner";
import { useAuth, roleHomePath } from "../../context/AuthContext";
import { uploadKycDocument } from "../../lib/authApi";

export function PendingValidation() {
  const navigate = useNavigate();
  const { session, clearSession, refreshUser } = useAuth();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [justUploaded, setJustUploaded] = useState(false);

  if (!session) {
    return <Navigate to="/login" replace />;
  }

  const { entreprise } = session.user;

  if (entreprise.statut_kyc === "valide") {
    return <Navigate to={roleHomePath(session.user.role)} replace />;
  }

  async function handleFileSelected(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !session) return;

    setUploading(true);
    setUploadError(null);
    try {
      await uploadKycDocument(session.user.entreprise.id, file, session.accessToken);
      await refreshUser();
      setJustUploaded(true);
    } catch {
      setUploadError("Le téléversement a échoué. Réessayez dans quelques instants.");
    } finally {
      setUploading(false);
    }
  }

  function handleLogout() {
    clearSession();
    navigate("/login", { replace: true });
  }

  const documentsDejaFournis = Boolean(entreprise.kyc_document_url) || justUploaded;

  return (
    <AuthLayout>
      <div className="auth-card">
        {entreprise.statut_kyc === "en_attente" ? (
          <span className="auth-status-badge auth-status-badge--pending">Vérification en cours</span>
        ) : (
          <span className="auth-status-badge auth-status-badge--rejected">Documents rejetés</span>
        )}

        <div className="auth-card-title auth-card-title--stacked">
          {entreprise.raison_sociale}
        </div>

        {entreprise.statut_kyc === "en_attente" && (
          <>
            <div className="auth-card-subtitle">
              Votre compte est en attente de validation par notre équipe. Vous pourrez accéder à
              votre espace dès que la vérification sera terminée.
            </div>

            {documentsDejaFournis ? (
              <div className="auth-info-banner">En cours de vérification par notre équipe.</div>
            ) : (
              <div className="auth-info-banner">
                Aucun document n'a encore été fourni. Téléversez votre RCCM, votre NINEA et une
                pièce d'identité du représentant légal (regroupés dans un seul fichier PDF si
                possible) pour accélérer la vérification.
              </div>
            )}
          </>
        )}

        {entreprise.statut_kyc === "rejete" && (
          <>
            <div className="auth-card-subtitle">
              Les documents fournis n'ont pas pu être validés.
            </div>
            <div className="auth-error-banner">
              {entreprise.motif_rejet_kyc
                ? entreprise.motif_rejet_kyc
                : "Aucun motif détaillé n'a été renseigné. Contactez le support pour plus d'informations."}
            </div>
            <div className="auth-info-banner">
              Vous pouvez soumettre à nouveau vos documents ci-dessous.
            </div>
          </>
        )}

        {(!documentsDejaFournis || entreprise.statut_kyc === "rejete") && (
          <>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              style={{ display: "none" }}
              onChange={handleFileSelected}
            />
            {uploadError && <ErrorBanner message={uploadError} />}
            <button
              type="button"
              className="auth-submit"
              disabled={uploading}
              onClick={() => fileInputRef.current?.click()}
            >
              {uploading ? "Téléversement..." : "Téléverser mes documents"}
            </button>
          </>
        )}

        <button type="button" className="auth-submit-secondary" onClick={handleLogout}>
          Se déconnecter
        </button>
      </div>
    </AuthLayout>
  );
}
