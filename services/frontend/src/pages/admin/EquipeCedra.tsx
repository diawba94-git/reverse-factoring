import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../../context/AuthContext";
import { Badge } from "../../components/admin/Badge";
import { Modal } from "../../components/admin/Modal";
import { FormField } from "../../components/auth/FormField";
import { ErrorBanner } from "../../components/auth/ErrorBanner";
import { ApiError } from "../../lib/apiClient";
import { modifierUtilisateurAdmin, type UtilisateurOut } from "../../lib/adminApi";
import {
  creerMembreEquipe,
  listerEquipeInterne,
  listerSessions,
  revoquerSession,
  revoquerToutesLesSessions,
  type SessionOut,
} from "../../lib/equipeApi";

function formatDate(value: string): string {
  return new Date(value).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" });
}

function AjouterMembreModal({
  entrepriseId,
  onClose,
  onCreated,
}: {
  entrepriseId: string;
  onClose: () => void;
  onCreated: (u: UtilisateurOut) => void;
}) {
  const { session } = useAuth();
  const token = session?.accessToken ?? "";
  const [nom, setNom] = useState("");
  const [telephone, setTelephone] = useState("");
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const utilisateur = await creerMembreEquipe(
        { entreprise_id: entrepriseId, nom, telephone, email, mot_de_passe: motDePasse },
        token,
      );
      onCreated(utilisateur);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Une erreur est survenue. Réessayez.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      title="Ajouter un membre de l'équipe Cedra"
      subtitle="Communiquez le mot de passe initial à la personne concernée par un canal séparé."
      onClose={onClose}
    >
      <form onSubmit={handleSubmit}>
        <FormField label="Nom complet" value={nom} onChange={(e) => setNom(e.target.value)} />
        <FormField label="Téléphone" type="tel" value={telephone} onChange={(e) => setTelephone(e.target.value)} />
        <FormField label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <FormField
          label="Mot de passe initial"
          type="password"
          value={motDePasse}
          onChange={(e) => setMotDePasse(e.target.value)}
        />
        {error && <ErrorBanner message={error} />}
        <div className="admin-modal-actions">
          <button type="button" className="admin-button admin-button--secondary" onClick={onClose}>
            Annuler
          </button>
          <button type="submit" className="admin-button admin-button--primary" disabled={submitting}>
            {submitting ? "Création..." : "Créer le compte"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function SessionsPanel({ utilisateur, token }: { utilisateur: UtilisateurOut; token: string }) {
  const [sessions, setSessions] = useState<SessionOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  function recharger() {
    setSessions(null);
    setError(null);
    listerSessions(utilisateur.id, token)
      .then(setSessions)
      .catch(() => setError("Impossible de charger les sessions."));
  }

  useEffect(recharger, [utilisateur.id, token]);

  async function handleRevoquer(sessionId: string) {
    setBusyId(sessionId);
    try {
      await revoquerSession(sessionId, token);
      recharger();
    } catch {
      setError("Impossible de révoquer cette session.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleRevoquerTout() {
    setBusyId("*");
    try {
      await revoquerToutesLesSessions(utilisateur.id, token);
      recharger();
    } catch {
      setError("Impossible de révoquer les sessions.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="admin-panel admin-panel-utilisateurs">
      <div className="admin-panel-header">
        <div>
          <div className="admin-panel-title">Sessions actives</div>
          <div className="admin-panel-subtitle">{utilisateur.nom ?? utilisateur.telephone}</div>
        </div>
        <button
          type="button"
          className="admin-button admin-button--danger"
          disabled={busyId === "*"}
          onClick={handleRevoquerTout}
        >
          Fermer toutes les sessions
        </button>
      </div>

      {error && <ErrorBanner message={error} />}
      {!error && sessions === null && (
        <div className="admin-loading-state">
          <span className="admin-spinner" />
          Chargement...
        </div>
      )}
      {sessions !== null && sessions.length === 0 && <div className="admin-empty-state">Aucune session.</div>}

      {sessions !== null && sessions.length > 0 && (
        <table className="admin-table">
          <thead>
            <tr>
              <th>Appareil</th>
              <th>Adresse IP</th>
              <th>Ouverte le</th>
              <th>Statut</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.id}>
                <td style={{ maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {s.user_agent ?? "Inconnu"}
                </td>
                <td>{s.ip_address ?? "—"}</td>
                <td>{formatDate(s.created_at)}</td>
                <td>{s.revoked ? <Badge tone="neutral">Révoquée</Badge> : <Badge tone="success">Active</Badge>}</td>
                <td>
                  {!s.revoked && (
                    <button
                      type="button"
                      className="admin-button admin-button--secondary admin-button--small"
                      disabled={busyId === s.id}
                      onClick={() => handleRevoquer(s.id)}
                    >
                      Révoquer
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export function EquipeCedra() {
  const { session } = useAuth();
  const token = session?.accessToken ?? "";
  const entrepriseId = session?.user.entreprise.id ?? "";

  const [membres, setMembres] = useState<UtilisateurOut[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [rowError, setRowError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  function recharger() {
    if (!token) return;
    setMembres(null);
    setLoadError(null);
    listerEquipeInterne(token)
      .then(setMembres)
      .catch(() => setLoadError("Impossible de charger l'équipe Cedra."));
  }

  useEffect(recharger, [token]);

  async function handleToggleActif(u: UtilisateurOut) {
    setRowError(null);
    setBusyId(u.id);
    try {
      await modifierUtilisateurAdmin(u.id, { compte_actif: !u.compte_actif }, token);
      recharger();
    } catch (err) {
      setRowError(err instanceof ApiError ? err.message : "Impossible de modifier ce compte.");
    } finally {
      setBusyId(null);
    }
  }

  const selected = membres?.find((m) => m.id === selectedId) ?? null;

  return (
    <div className="admin-layout" style={{ padding: 0 }}>
      <div className="admin-panel admin-panel-entreprises">
        <div className="admin-panel-header">
          <div>
            <div className="admin-panel-title">Utilisateurs internes</div>
            <div className="admin-panel-subtitle">Équipe Cedra (rôle admin).</div>
          </div>
          <button type="button" className="admin-button admin-button--primary admin-button--small" onClick={() => setShowAdd(true)}>
            Ajouter
          </button>
        </div>

        {rowError && <ErrorBanner message={rowError} />}
        {loadError && <ErrorBanner message={loadError} />}
        {!loadError && membres === null && (
          <div className="admin-loading-state">
            <span className="admin-spinner" />
            Chargement...
          </div>
        )}
        {membres !== null && membres.length === 0 && <div className="admin-empty-state">Aucun membre interne.</div>}

        {membres !== null && membres.length > 0 && (
          <div className="admin-entreprise-list">
            {membres.map((m) => (
              <div key={m.id} className={`admin-entreprise-row ${selectedId === m.id ? "is-selected" : ""}`} style={{ cursor: "default" }}>
                <div className="admin-entreprise-row-top">
                  <span className="admin-entreprise-nom">{m.nom ?? m.telephone}</span>
                  {m.compte_actif ? <Badge tone="success">Actif</Badge> : <Badge tone="danger">Désactivé</Badge>}
                </div>
                <span className="admin-entreprise-type">{m.email ?? m.telephone}</span>
                <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                  <button
                    type="button"
                    className="admin-button admin-button--secondary admin-button--small"
                    onClick={() => setSelectedId(m.id)}
                  >
                    Sessions
                  </button>
                  <button
                    type="button"
                    className="admin-button admin-button--secondary admin-button--small"
                    disabled={busyId === m.id}
                    onClick={() => handleToggleActif(m)}
                  >
                    {m.compte_actif ? "Désactiver" : "Réactiver"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {selected ? (
        <SessionsPanel utilisateur={selected} token={token} />
      ) : (
        <div className="admin-panel admin-panel-utilisateurs">
          <div className="admin-empty-state">Sélectionnez un membre pour voir ses sessions actives.</div>
        </div>
      )}

      {showAdd && (
        <AjouterMembreModal
          entrepriseId={entrepriseId}
          onClose={() => setShowAdd(false)}
          onCreated={() => {
            setShowAdd(false);
            recharger();
          }}
        />
      )}
    </div>
  );
}
