import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { obtenirEntreprise } from "../../lib/entreprisesApi";
import type { EntrepriseOut } from "../../lib/adminApi";
import { FORME_JURIDIQUE_LABELS } from "../../lib/roles";

export function AcheteurParametres() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [entreprise, setEntreprise] = useState<EntrepriseOut | null>(null);

  useEffect(() => {
    obtenirEntreprise(session!.user.entreprise.id, token).then(setEntreprise).catch(() => {});
  }, [session, token]);

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Paramètres</h1>
          <div className="sub">Informations de l'entreprise et KYC</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        <div className="panel">
          {entreprise && (
            <>
              <h2 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 4px" }}>{entreprise.raison_sociale}</h2>
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 5,
                  fontSize: 11,
                  fontWeight: 600,
                  color: entreprise.statut_kyc === "valide" ? "var(--green)" : "var(--amber)",
                  background: entreprise.statut_kyc === "valide" ? "var(--green-soft)" : "#FBF0E1",
                  padding: "3px 10px",
                  borderRadius: 20,
                  marginBottom: 16,
                }}
              >
                {entreprise.statut_kyc === "valide" ? "✓ KYC validé" : entreprise.statut_kyc === "rejete" ? "KYC rejeté" : "KYC en attente"}
              </div>
              <div className="settings-grid">
                <div className="settings-field">
                  <label>NINEA</label>
                  <input type="text" value={entreprise.ninea ?? "—"} disabled />
                </div>
                <div className="settings-field">
                  <label>Forme juridique</label>
                  <input
                    type="text"
                    value={entreprise.forme_juridique ? FORME_JURIDIQUE_LABELS[entreprise.forme_juridique] : "—"}
                    disabled
                  />
                </div>
                <div className="settings-field">
                  <label>Adresse</label>
                  <input type="text" value={entreprise.adresse ?? "—"} disabled />
                </div>
                <div className="settings-field">
                  <label>Téléphone</label>
                  <input type="text" value={entreprise.contact_telephone ?? "—"} disabled />
                </div>
              </div>
            </>
          )}
        </div>
      </main>
    </>
  );
}
