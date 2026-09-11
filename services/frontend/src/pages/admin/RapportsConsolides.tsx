import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { ErrorBanner } from "../../components/auth/ErrorBanner";
import { obtenirRapport, type RapportPeriodeOut } from "../../lib/rapportsApi";

function formatMontant(value: string): string {
  return `${Number(value).toLocaleString("fr-FR")} FCFA`;
}

export function RapportsConsolides() {
  const { session } = useAuth();
  const token = session?.accessToken ?? "";

  const [periode, setPeriode] = useState<"mois" | "trimestre">("mois");
  const [rapport, setRapport] = useState<RapportPeriodeOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    setRapport(null);
    setError(null);
    obtenirRapport(periode, token)
      .then(setRapport)
      .catch(() => setError("Impossible de générer le rapport."));
  }, [periode, token]);

  const lignes = rapport
    ? [
        { label: "Factures émises", value: String(rapport.nombre_factures) },
        { label: "Montant total facturé", value: formatMontant(rapport.montant_total_factures) },
        { label: "Avances accordées", value: String(rapport.nombre_avances) },
        { label: "Volume total avancé", value: formatMontant(rapport.montant_total_avance_verse) },
        { label: "Frais plateforme perçus", value: formatMontant(rapport.montant_total_frais_plateforme) },
        { label: "Montant total remboursé", value: formatMontant(rapport.montant_total_rembourse) },
      ]
    : [];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 18, alignItems: "start" }}>
      <div className="admin-panel">
        <div className="admin-panel-title">Rapport consolidé</div>
        <div className="admin-panel-subtitle">Toutes interfaces confondues.</div>

        <div style={{ display: "flex", flexDirection: "column", gap: 7, marginTop: 18 }}>
          <span style={{ fontSize: 11.5, fontWeight: 500, color: "var(--color-text-muted)" }}>Périodicité</span>
          <div style={{ display: "flex", gap: 8 }}>
            {(["mois", "trimestre"] as const).map((p) => (
              <button
                key={p}
                type="button"
                className={`admin-button ${periode === p ? "admin-button--primary" : "admin-button--secondary"}`}
                style={{ flex: 1 }}
                onClick={() => setPeriode(p)}
              >
                {p === "mois" ? "Ce mois-ci" : "Ce trimestre"}
              </button>
            ))}
          </div>
        </div>

        {rapport && (
          <div style={{ fontSize: 11.5, color: "var(--color-text-faint)", marginTop: 16 }}>
            Du {new Date(rapport.debut).toLocaleDateString("fr-FR")} au{" "}
            {new Date(rapport.fin).toLocaleDateString("fr-FR")}
          </div>
        )}
      </div>

      <div className="admin-panel">
        <div className="admin-panel-title">Aperçu</div>
        {error && <ErrorBanner message={error} />}
        {!error && !rapport && (
          <div className="admin-loading-state">
            <span className="admin-spinner" />
            Chargement...
          </div>
        )}
        {rapport && (
          <div style={{ display: "flex", flexDirection: "column", marginTop: 16 }}>
            {lignes.map((l) => (
              <div
                key={l.label}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "baseline",
                  gap: 12,
                  padding: "11px 0",
                  borderBottom: "1px solid var(--color-divider)",
                }}
              >
                <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>{l.label}</span>
                <span style={{ fontSize: 15, fontWeight: 600 }}>{l.value}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
