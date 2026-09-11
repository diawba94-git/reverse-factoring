import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { ErrorBanner } from "../../components/auth/ErrorBanner";
import { listerJournalAudit, type JournalAuditOut } from "../../lib/journalAuditApi";

const ENTITES: { label: string; value: string | undefined }[] = [
  { label: "Toutes", value: undefined },
  { label: "Entreprise", value: "Entreprise" },
  { label: "Utilisateur", value: "Utilisateur" },
  { label: "GrilleTarifaire", value: "GrilleTarifaire" },
  { label: "Remboursement", value: "Remboursement" },
  { label: "ArticleFaq", value: "ArticleFaq" },
];

function formatDate(value: string): string {
  return new Date(value).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "medium" });
}

export function LogsTechniques() {
  const { session } = useAuth();
  const token = session?.accessToken ?? "";

  const [entiteType, setEntiteType] = useState<string | undefined>(undefined);
  const [entries, setEntries] = useState<JournalAuditOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    setEntries(null);
    setError(null);
    listerJournalAudit({ entite_type: entiteType }, token)
      .then(setEntries)
      .catch(() => setError("Impossible de charger le journal d'audit."));
  }, [entiteType, token]);

  return (
    <div className="admin-panel">
      <div className="admin-panel-header">
        <div>
          <div className="admin-panel-title">Journal d'audit applicatif</div>
          <div className="admin-panel-subtitle">
            Trace toutes les actions métier (créations, modifications, décisions KYC...). Fenêtre : 500 entrées les
            plus récentes.
          </div>
        </div>
      </div>

      <div className="admin-filter-tabs">
        {ENTITES.map((f) => (
          <button
            key={f.label}
            type="button"
            className={`admin-filter-tab ${entiteType === f.value ? "is-active" : ""}`}
            onClick={() => setEntiteType(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error && <ErrorBanner message={error} />}
      {!error && entries === null && (
        <div className="admin-loading-state">
          <span className="admin-spinner" />
          Chargement...
        </div>
      )}
      {entries !== null && entries.length === 0 && <div className="admin-empty-state">Aucune entrée pour ce filtre.</div>}

      {entries !== null && entries.length > 0 && (
        <table className="admin-table">
          <thead>
            <tr>
              <th>Horodatage</th>
              <th>Entité</th>
              <th>Action</th>
              <th>Détail</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr key={e.id}>
                <td style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--color-text-muted)" }}>
                  {formatDate(e.horodatage)}
                </td>
                <td>
                  {e.entite_type}
                  <div style={{ fontSize: 11, color: "var(--color-text-faint)" }}>{e.entite_id.slice(0, 8)}</div>
                </td>
                <td>{e.action}</td>
                <td style={{ fontFamily: "var(--font-mono)", fontSize: 11.5, color: "var(--color-text-secondary)" }}>
                  {JSON.stringify(e.valeur_apres)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
