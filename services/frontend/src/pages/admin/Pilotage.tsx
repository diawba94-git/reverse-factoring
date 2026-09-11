import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { ErrorBanner } from "../../components/auth/ErrorBanner";
import { obtenirDashboardAdmin, type DashboardAdminOut } from "../../lib/dashboardApi";
import { TYPE_ENTREPRISE_LABELS } from "../../lib/roles";
import type { TypeEntreprise } from "../../lib/authApi";

function formatMontant(value: string): string {
  return `${Number(value).toLocaleString("fr-FR")} FCFA`;
}

function KpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="admin-panel" style={{ flex: 1 }}>
      <div
        style={{
          fontSize: 10.5,
          fontWeight: 600,
          letterSpacing: "0.07em",
          color: "var(--color-text-muted)",
          textTransform: "uppercase",
        }}
      >
        {label}
      </div>
      <div style={{ fontSize: 22, fontWeight: 600, marginTop: 9 }}>{value}</div>
    </div>
  );
}

export function Pilotage() {
  const { session } = useAuth();
  const token = session?.accessToken ?? "";

  const [data, setData] = useState<DashboardAdminOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    setData(null);
    setError(null);
    obtenirDashboardAdmin(token)
      .then(setData)
      .catch(() => setError("Impossible de charger le tableau de bord."));
  }, [token]);

  if (error) return <ErrorBanner message={error} />;

  if (!data) {
    return (
      <div className="admin-loading-state">
        <span className="admin-spinner" />
        Chargement...
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
        <KpiCard label="Entreprises inscrites" value={data.nombre_entreprises} />
        <KpiCard label="Utilisateurs" value={data.nombre_utilisateurs} />
        <KpiCard label="Factures" value={data.nombre_factures} />
        <KpiCard label="Avances" value={data.nombre_avances} />
      </div>

      <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
        <KpiCard label="Volume total avancé" value={formatMontant(data.montant_total_avance_verse)} />
        <KpiCard label="Frais plateforme perçus" value={formatMontant(data.montant_total_frais_plateforme)} />
        <KpiCard label="Tickets support ouverts" value={data.tickets_ouverts} />
      </div>

      <div className="admin-panel">
        <div className="admin-panel-title">Répartition des entreprises par type</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 16 }}>
          {(Object.entries(data.entreprises_par_type) as [TypeEntreprise, number][]).map(([type, count]) => {
            const pct = data.nombre_entreprises > 0 ? (count / data.nombre_entreprises) * 100 : 0;
            return (
              <div key={type} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5 }}>
                  <span style={{ color: "var(--color-text-secondary)" }}>{TYPE_ENTREPRISE_LABELS[type] ?? type}</span>
                  <span style={{ color: "var(--color-text-muted)" }}>{count}</span>
                </div>
                <div style={{ height: 6, borderRadius: 3, background: "var(--color-bg-subtle)", overflow: "hidden" }}>
                  <div style={{ height: "100%", borderRadius: 3, width: `${pct}%`, background: "var(--color-primary)" }} />
                </div>
              </div>
            );
          })}
          {Object.keys(data.entreprises_par_type).length === 0 && (
            <div className="admin-empty-state">Aucune entreprise inscrite pour l'instant.</div>
          )}
        </div>
      </div>
    </div>
  );
}
