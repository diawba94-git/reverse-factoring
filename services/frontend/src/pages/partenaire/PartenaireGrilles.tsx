import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { listerGrillesActives, type GrilleTarifaireOut } from "../../lib/grillesApi";

function pct(v: string, decimals = 2): string {
  return `${(Number(v) * 100).toFixed(decimals)} %`;
}

export function PartenaireGrilles() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [grille, setGrille] = useState<GrilleTarifaireOut | null>(null);

  useEffect(() => {
    listerGrillesActives(token).then((gs) => setGrille(gs[0] ?? null)).catch(() => setGrille(null));
  }, [token]);

  const proportionAffichee = grille ? `${Math.round(Number(grille.proportion_partenaire) * 100)}/100` : "—";

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Grilles tarifaires</h1>
          <div className="sub">Grille active sur votre portefeuille — configurée par Cedra</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        {!grille ? (
          <div className="panel">Aucune grille tarifaire active pour le moment.</div>
        ) : (
          <div className="facture-master" style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 16, alignItems: "start" }}>
            <div className="panel">
              <h2 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 4px" }}>{grille.nom}</h2>
              <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 14 }}>
                Lecture seule — seul l'admin Cedra peut modifier une grille
              </div>
              <div className="grille-form">
                <div className="grille-field">
                  <label>Type de partenaire</label>
                  <input value={grille.type_partenaire === "imf" ? "IMF" : "Banque"} disabled />
                </div>
                <div className="grille-field">
                  <label>Taux total à {grille.duree_minimum_jours} jours</label>
                  <input value={pct(grille.taux_total_minimum)} disabled />
                </div>
                <div className="grille-field">
                  <label>Taux total à {grille.duree_maximum_jours} jours</label>
                  <input value={pct(grille.taux_total_maximum)} disabled />
                </div>
                <div className="grille-field">
                  <label>Votre part (proportion)</label>
                  <input value={proportionAffichee} disabled />
                </div>
                <div className="grille-field">
                  <label>Durée min/max</label>
                  <input value={`${grille.duree_minimum_jours} - ${grille.duree_maximum_jours} jours`} disabled />
                </div>
                <div className="grille-field">
                  <label>Taux d'avance</label>
                  <input value={pct(grille.taux_avance, 0)} disabled />
                </div>
              </div>
            </div>
            <div className="panel">
              <h2 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 10px" }}>Votre part par durée</h2>
              <table className="preview-table">
                <thead>
                  <tr>
                    <th>Durée</th>
                    <th>Taux total</th>
                    <th>Votre part</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>{grille.duree_minimum_jours} jours</td>
                    <td>{pct(grille.taux_total_minimum)}</td>
                    <td className="ok">{pct((Number(grille.taux_total_minimum) * Number(grille.proportion_partenaire)).toString())}</td>
                  </tr>
                  <tr>
                    <td>{grille.duree_maximum_jours} jours</td>
                    <td>{pct(grille.taux_total_maximum)}</td>
                    <td className="ok">{pct((Number(grille.taux_total_maximum) * Number(grille.proportion_partenaire)).toString())}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
