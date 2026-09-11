import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../../context/AuthContext";
import { usePme } from "../../context/PmeContext";
import { Modal } from "../../components/admin/Modal";
import { EntrepriseUserPanel } from "../../components/admin/EntrepriseUserPanel";
import { FormField } from "../../components/auth/FormField";
import { ErrorBanner } from "../../components/auth/ErrorBanner";
import { ApiError, apiFetch } from "../../lib/apiClient";
import { inviterCollegue } from "../../lib/pmeApi";

type Collegue = {
  id: string;
  nom: string | null;
  telephone: string;
  role: string;
  compte_actif: boolean;
  derniere_connexion: string | null;
};

function InviterModal({
  entrepriseId,
  token,
  onClose,
  onInvited,
}: {
  entrepriseId: string;
  token: string;
  onClose: () => void;
  onInvited: (message: string) => void;
}) {
  const [nom, setNom] = useState("");
  const [telephone, setTelephone] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const invitation = await inviterCollegue(entrepriseId, { nom, telephone, email, role: "membre_pme" }, token);
      onInvited(
        `Invitation créée pour ${nom}. Aucun canal SMS/email n'est encore branché : partagez ce jeton d'activation ` +
          `manuellement (valable jusqu'au ${new Date(invitation.expires_at).toLocaleString("fr-FR")}) : ${invitation.token}`,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Une erreur est survenue. Réessayez.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal title="Inviter un collègue" subtitle="Rôle attribué : Membre PME (seul rôle disponible pour votre entreprise)." onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <FormField label="Nom complet" value={nom} onChange={(e) => setNom(e.target.value)} />
        <FormField label="Téléphone" type="tel" value={telephone} onChange={(e) => setTelephone(e.target.value)} />
        <FormField label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        {error && <ErrorBanner message={error} />}
        <div className="admin-modal-actions">
          <button type="button" className="admin-button admin-button--secondary" onClick={onClose}>
            Annuler
          </button>
          <button type="submit" className="admin-button admin-button--primary" disabled={submitting}>
            {submitting ? "Envoi..." : "Envoyer l'invitation"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function EquipeMembrePme() {
  const { session } = useAuth();
  const { pmeId, pmeNom } = usePme();
  const token = session?.accessToken ?? "";

  const [collegues, setCollegues] = useState<Collegue[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showInvite, setShowInvite] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  function recharger() {
    if (!token) return;
    apiFetch<Collegue[]>("/utilisateurs", { token })
      .then(setCollegues)
      .catch(() => setError("Impossible de charger l'équipe."));
  }

  useEffect(recharger, [token]);

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Utilisateurs de l'entreprise</h1>
          <div className="sub">
            {pmeNom ?? "…"} — {collegues?.length ?? "…"} membre{(collegues?.length ?? 0) > 1 ? "s" : ""}
          </div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        {successMessage && (
          <div
            style={{
              background: "var(--green-soft)",
              color: "var(--green-dark)",
              borderRadius: 8,
              padding: "11px 14px",
              fontSize: 12,
              marginBottom: 14,
            }}
          >
            {successMessage}
          </div>
        )}
        {error && <ErrorBanner message={error} />}
        {collegues !== null && collegues.length === 0 && <div className="sub">Aucun collègue pour l'instant.</div>}

        <div className="panel">
          {collegues?.map((c) => (
            <div className="invite-row" key={c.id}>
              <div className="invite-avatar">{(c.nom ?? "?").charAt(0).toUpperCase()}</div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 12.8 }}>{c.nom ?? "(sans nom)"}</div>
                <div style={{ fontSize: 11, color: "var(--muted)" }}>
                  Membre PME
                  {c.id === session?.user.id ? " · vous" : !c.compte_actif ? " · invitation en attente" : ""}
                </div>
              </div>
            </div>
          ))}
          <button type="button" className="btn-primary" style={{ marginTop: 14 }} onClick={() => setShowInvite(true)}>
            + Inviter un membre
          </button>
        </div>
      </main>

      {showInvite && pmeId && (
        <InviterModal
          entrepriseId={pmeId}
          token={token}
          onClose={() => setShowInvite(false)}
          onInvited={(message) => {
            setShowInvite(false);
            setSuccessMessage(message);
            recharger();
          }}
        />
      )}
    </>
  );
}

export function GestionUtilisateursPme() {
  const { session } = useAuth();
  const { isAdmin, pmeEntreprise } = usePme();
  const token = session?.accessToken ?? "";

  if (isAdmin) {
    return (
      <>
        <header className="topbar">
          <div>
            <h1>Utilisateurs de l'entreprise</h1>
            <div className="sub">{pmeEntreprise?.raison_sociale ?? "…"}</div>
          </div>
        </header>
        <main style={{ padding: "20px 24px 30px" }}>
          {!pmeEntreprise ? (
            <div className="admin-loading-state">
              <span className="admin-spinner" />
              Chargement du profil de l'entreprise...
            </div>
          ) : (
            <EntrepriseUserPanel entreprise={pmeEntreprise} token={token} />
          )}
        </main>
      </>
    );
  }

  return <EquipeMembrePme />;
}
