export function Parametres() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
      <div className="admin-panel">
        <div className="admin-panel-title">Pays desservis</div>
        <div className="admin-panel-subtitle">
          Cadre UEMOA / BCEAO : l'ouverture d'un nouveau pays n'exige pas de nouvelle grille tarifaire.
        </div>
        <div style={{ marginTop: 16, border: "1px solid var(--color-primary-tint-border)", background: "var(--color-primary-tint-bg)", borderRadius: "var(--radius-md)", padding: 14 }}>
          <div style={{ fontSize: 13.5, fontWeight: 500, color: "var(--color-success-text)" }}>Sénégal</div>
          <div style={{ fontSize: 11.5, color: "var(--color-text-muted)", marginTop: 2 }}>Seul pays actif pour l'instant.</div>
        </div>
        <div className="admin-empty-state" style={{ marginTop: 12, padding: 20 }}>
          L'extension à d'autres pays UEMOA n'est pas encore configurable depuis cet écran.
        </div>
      </div>

      <div className="admin-panel">
        <div className="admin-panel-title">Devise</div>
        <div className="admin-panel-subtitle">Le multi-devises est hors périmètre actuel : la plateforme opère en franc CFA.</div>
        <div style={{ marginTop: 16, border: "1px solid var(--color-primary-tint-border)", background: "var(--color-primary-tint-bg)", borderRadius: "var(--radius-md)", padding: 14, textAlign: "center", fontWeight: 600, color: "var(--color-success-text)" }}>
          FCFA (XOF)
        </div>
      </div>
    </div>
  );
}
