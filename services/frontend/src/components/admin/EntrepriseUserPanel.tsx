import { useEffect, useState, type FormEvent } from "react";
import { Badge } from "./Badge";
import { Modal } from "./Modal";
import { FormField } from "../auth/FormField";
import { ErrorBanner } from "../auth/ErrorBanner";
import { ApiError } from "../../lib/apiClient";
import {
  creerUtilisateurAdmin,
  listerUtilisateursEntreprise,
  modifierUtilisateurAdmin,
  type EntrepriseOut,
  type UtilisateurOut,
} from "../../lib/adminApi";
import type { RoleUtilisateur } from "../../lib/authApi";
import { ROLES_PAR_TYPE_ENTREPRISE, ROLE_LABELS, STATUT_KYC_LABELS, TYPE_ENTREPRISE_LABELS } from "../../lib/roles";

function statutBadgeTone(statut: EntrepriseOut["statut_kyc"]) {
  if (statut === "valide") return "success" as const;
  if (statut === "rejete") return "danger" as const;
  return "warning" as const;
}

function formatDerniereConnexion(value: string | null): string {
  if (!value) return "Jamais connecté";
  return new Date(value).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" });
}

type FormState = { nom: string; telephone: string; email: string; role: RoleUtilisateur | "" };

function AjouterUtilisateurModal({
  entreprise,
  token,
  onClose,
  onCreated,
}: {
  entreprise: EntrepriseOut;
  token: string;
  onClose: () => void;
  onCreated: (utilisateur: UtilisateurOut, motDePasseTemporaire: string) => void;
}) {
  const rolesDisponibles = ROLES_PAR_TYPE_ENTREPRISE[entreprise.type];
  const [form, setForm] = useState<FormState>({
    nom: "",
    telephone: "",
    email: "",
    role: rolesDisponibles.length === 1 ? rolesDisponibles[0] : "",
  });
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<keyof FormState, string>>>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function setField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    const errors: Partial<Record<keyof FormState, string>> = {};
    if (form.nom.trim().length < 2) errors.nom = "Nom trop court";
    if (form.telephone.trim().length < 6) errors.telephone = "Numéro invalide";
    if (!form.email.trim()) errors.email = "Champ requis";
    if (!form.role) errors.role = "Sélectionnez un rôle";
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    try {
      const { mot_de_passe_temporaire, ...utilisateur } = await creerUtilisateurAdmin(
        entreprise.id,
        { nom: form.nom.trim(), telephone: form.telephone.trim(), email: form.email.trim(), role: form.role as RoleUtilisateur },
        token,
      );
      onCreated(utilisateur, mot_de_passe_temporaire);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("Ce numéro de téléphone est déjà utilisé par un autre compte.");
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Une erreur est survenue. Réessayez.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal title="Ajouter un utilisateur" subtitle={`Entreprise : ${entreprise.raison_sociale}`} onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <FormField
          label="Nom complet"
          value={form.nom}
          onChange={(e) => setField("nom", e.target.value)}
          error={fieldErrors.nom}
        />
        <FormField
          label="Téléphone"
          type="tel"
          placeholder="+221 77 000 00 00"
          value={form.telephone}
          onChange={(e) => setField("telephone", e.target.value)}
          error={fieldErrors.telephone}
        />
        <FormField
          label="Email"
          type="email"
          value={form.email}
          onChange={(e) => setField("email", e.target.value)}
          error={fieldErrors.email}
        />
        <div className="admin-field">
          <span className="admin-field-label">Rôle</span>
          <select
            className={`admin-select ${fieldErrors.role ? "has-error" : ""}`}
            value={form.role}
            onChange={(e) => setField("role", e.target.value as RoleUtilisateur)}
          >
            <option value="" disabled>
              Sélectionnez un rôle
            </option>
            {rolesDisponibles.map((role) => (
              <option key={role} value={role}>
                {ROLE_LABELS[role]}
              </option>
            ))}
          </select>
          {fieldErrors.role && <span className="auth-field-error">{fieldErrors.role}</span>}
        </div>

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

function ConfirmationDesactivation({
  utilisateur,
  onCancel,
  onConfirm,
  submitting,
}: {
  utilisateur: UtilisateurOut;
  onCancel: () => void;
  onConfirm: () => void;
  submitting: boolean;
}) {
  return (
    <Modal title="Désactiver ce compte ?" onClose={onCancel}>
      <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "0 0 4px" }}>
        {utilisateur.nom ?? utilisateur.telephone} ne pourra plus se connecter tant que le compte n'est pas
        réactivé. Cette action est réversible.
      </p>
      <div className="admin-modal-actions">
        <button type="button" className="admin-button admin-button--secondary" onClick={onCancel}>
          Annuler
        </button>
        <button type="button" className="admin-button admin-button--danger" onClick={onConfirm} disabled={submitting}>
          {submitting ? "Désactivation..." : "Désactiver"}
        </button>
      </div>
    </Modal>
  );
}

export function EntrepriseUserPanel({ entreprise, token }: { entreprise: EntrepriseOut; token: string }) {
  const [utilisateurs, setUtilisateurs] = useState<UtilisateurOut[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [pendingDeactivation, setPendingDeactivation] = useState<UtilisateurOut | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);
  const [busyRowId, setBusyRowId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setUtilisateurs(null);
    setLoadError(null);
    setSuccessMessage(null);
    setRowError(null);
    setShowAddModal(false);
    setPendingDeactivation(null);
    setBusyRowId(null);

    listerUtilisateursEntreprise(entreprise.id, token)
      .then((data) => {
        if (!cancelled) setUtilisateurs(data);
      })
      .catch(() => {
        if (!cancelled) setLoadError("Impossible de charger les utilisateurs de cette entreprise.");
      });

    return () => {
      cancelled = true;
    };
  }, [entreprise.id, token]);

  function handleCreated(nouvelUtilisateur: UtilisateurOut, motDePasseTemporaire: string) {
    setUtilisateurs((prev) => (prev ? [nouvelUtilisateur, ...prev] : [nouvelUtilisateur]));
    setShowAddModal(false);
    setSuccessMessage(
      `Compte créé pour ${nouvelUtilisateur.nom ?? nouvelUtilisateur.telephone}. Un mot de passe temporaire a été ` +
        `envoyé par SMS/email. (Environnement de test — aucun canal réel n'est encore branché : ${motDePasseTemporaire})`,
    );
  }

  async function handleChangeRole(utilisateur: UtilisateurOut, role: RoleUtilisateur) {
    if (role === utilisateur.role) return;
    setRowError(null);
    setBusyRowId(utilisateur.id);
    try {
      const maj = await modifierUtilisateurAdmin(utilisateur.id, { role }, token);
      setUtilisateurs((prev) => prev?.map((u) => (u.id === utilisateur.id ? maj : u)) ?? prev);
    } catch (err) {
      setRowError(
        err instanceof ApiError ? err.message : "Impossible de modifier le rôle de cet utilisateur.",
      );
    } finally {
      setBusyRowId(null);
    }
  }

  async function handleConfirmDeactivation() {
    if (!pendingDeactivation) return;
    setBusyRowId(pendingDeactivation.id);
    try {
      const maj = await modifierUtilisateurAdmin(pendingDeactivation.id, { compte_actif: false }, token);
      setUtilisateurs((prev) => prev?.map((u) => (u.id === maj.id ? maj : u)) ?? prev);
      setPendingDeactivation(null);
    } catch (err) {
      setRowError(err instanceof ApiError ? err.message : "Impossible de désactiver ce compte.");
    } finally {
      setBusyRowId(null);
    }
  }

  async function handleReactiver(utilisateur: UtilisateurOut) {
    setRowError(null);
    setBusyRowId(utilisateur.id);
    try {
      const maj = await modifierUtilisateurAdmin(utilisateur.id, { compte_actif: true }, token);
      setUtilisateurs((prev) => prev?.map((u) => (u.id === maj.id ? maj : u)) ?? prev);
    } catch (err) {
      setRowError(err instanceof ApiError ? err.message : "Impossible de réactiver ce compte.");
    } finally {
      setBusyRowId(null);
    }
  }

  const rolesDisponibles = ROLES_PAR_TYPE_ENTREPRISE[entreprise.type];

  return (
    <div className="admin-panel admin-panel-utilisateurs">
      <div className="admin-panel-header">
        <div>
          <div className="admin-panel-title-row">
            <span className="admin-panel-title">{entreprise.raison_sociale}</span>
            <Badge tone={statutBadgeTone(entreprise.statut_kyc)}>{STATUT_KYC_LABELS[entreprise.statut_kyc]}</Badge>
          </div>
          <div className="admin-panel-subtitle">
            {TYPE_ENTREPRISE_LABELS[entreprise.type]} · Utilisateurs rattachés à cette entreprise
          </div>
        </div>
        <button type="button" className="admin-button admin-button--primary" onClick={() => setShowAddModal(true)}>
          Ajouter un utilisateur
        </button>
      </div>

      {successMessage && <div className="admin-success-banner">{successMessage}</div>}
      {rowError && <ErrorBanner message={rowError} />}

      {loadError && <ErrorBanner message={loadError} />}

      {!loadError && utilisateurs === null && (
        <div className="admin-loading-state">
          <span className="admin-spinner" />
          Chargement des utilisateurs...
        </div>
      )}

      {utilisateurs !== null && utilisateurs.length === 0 && (
        <div className="admin-empty-state">
          Aucun utilisateur pour cette entreprise pour l'instant. Utilisez « Ajouter un utilisateur » pour créer le
          premier compte.
        </div>
      )}

      {utilisateurs !== null && utilisateurs.length > 0 && (
        <table className="admin-table">
          <thead>
            <tr>
              <th>Nom</th>
              <th>Téléphone</th>
              <th>Rôle</th>
              <th>Statut</th>
              <th>Dernière connexion</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {utilisateurs.map((u) => (
              <tr key={u.id}>
                <td>{u.nom ?? "—"}</td>
                <td>{u.telephone}</td>
                <td>
                  {rolesDisponibles.length > 1 ? (
                    <select
                      className="admin-select"
                      value={u.role}
                      disabled={busyRowId === u.id}
                      onChange={(e) => handleChangeRole(u, e.target.value as RoleUtilisateur)}
                    >
                      {rolesDisponibles.map((role) => (
                        <option key={role} value={role}>
                          {ROLE_LABELS[role]}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <Badge tone="neutral">{ROLE_LABELS[u.role]}</Badge>
                  )}
                </td>
                <td>
                  {u.compte_actif ? <Badge tone="success">Actif</Badge> : <Badge tone="danger">Désactivé</Badge>}
                </td>
                <td>{formatDerniereConnexion(u.derniere_connexion)}</td>
                <td>
                  <div className="admin-table-actions">
                    {u.compte_actif ? (
                      <button
                        type="button"
                        className="admin-button admin-button--danger admin-button--small"
                        disabled={busyRowId === u.id}
                        onClick={() => setPendingDeactivation(u)}
                      >
                        Désactiver
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="admin-button admin-button--secondary admin-button--small"
                        disabled={busyRowId === u.id}
                        onClick={() => handleReactiver(u)}
                      >
                        Réactiver
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {showAddModal && (
        <AjouterUtilisateurModal
          entreprise={entreprise}
          token={token}
          onClose={() => setShowAddModal(false)}
          onCreated={handleCreated}
        />
      )}

      {pendingDeactivation && (
        <ConfirmationDesactivation
          utilisateur={pendingDeactivation}
          submitting={busyRowId === pendingDeactivation.id}
          onCancel={() => setPendingDeactivation(null)}
          onConfirm={handleConfirmDeactivation}
        />
      )}
    </div>
  );
}
