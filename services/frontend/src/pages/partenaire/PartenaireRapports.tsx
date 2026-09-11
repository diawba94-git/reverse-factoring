import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { obtenirRapportResume, telechargerRapport, type RapportResumeOut } from "../../lib/partenaireApi";
import { ApiError } from "../../lib/apiClient";

function fmt(v: string): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}

function VariationLabel({ pct }: { pct: string | null }) {
  if (pct === null) return <div style={{ fontSize: 11, color: "var(--muted)" }}>Pas de référence le mois dernier</div>;
  const valeur = Number(pct);
  const hausse = valeur >= 0;
  return (
    <div style={{ fontSize: 11, color: hausse ? "var(--green)" : "var(--red)", fontWeight: 600 }}>
      {hausse ? "▲" : "▼"} {Math.abs(valeur).toFixed(1)}% vs mois dernier
    </div>
  );
}

export function PartenaireRapports() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [resume, setResume] = useState<RapportResumeOut | null>(null);
  const [telechargementEnCours, setTelechargementEnCours] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    obtenirRapportResume(token).then(setResume).catch(() => setResume(null));
  }, [token]);

  const montantMax = resume ? Math.max(...resume.volume_par_mois.map((m) => Number(m.montant)), 1) : 1;

  async function handleTelecharger(periode: "mensuel" | "trimestriel" | "semestriel") {
    setErreur(null);
    setTelechargementEnCours(periode);
    try {
      await telechargerRapport(periode, token);
    } catch (e) {
      setErreur(e instanceof ApiError ? e.message : "Impossible de générer le rapport.");
    } finally {
      setTelechargementEnCours(null);
    }
  }

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Rapports</h1>
          <div className="sub">Performance de votre portefeuille</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        {resume && (
          <>
            <div className="facture-master" style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 16, alignItems: "start" }}>
              <div className="panel">
                <h2 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 4px" }}>Volume financé par mois</h2>
                <div className="sub" style={{ fontSize: 11.5, color: "var(--muted)", marginBottom: 6 }}>
                  6 derniers mois — FCFA
                </div>
                <div className="bar-chart">
                  {resume.volume_par_mois.map((m, i) => {
                    const hauteurPct = Math.max(4, Math.round((Number(m.montant) / montantMax) * 100));
                    const dernier = i === resume.volume_par_mois.length - 1;
                    return (
                      <div
                        key={m.mois + i}
                        className="bar"
                        style={{ height: `${hauteurPct}%`, background: dernier ? "var(--green)" : undefined }}
                        title={`${fmt(m.montant)} FCFA`}
                      >
                        <span className="lbl">{m.mois}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="panel">
                <h2 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 10px" }}>Indicateurs clés — ce mois</h2>
                <div className="stat-card" style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 11, color: "var(--muted)" }}>Montant financé</div>
                  <div className="v">{fmt(resume.montant_finance_ce_mois)} FCFA</div>
                  <VariationLabel pct={resume.variation_montant_finance_pct} />
                </div>
                <div className="stat-card" style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 11, color: "var(--muted)" }}>Frais générés (votre part)</div>
                  <div className="v">{fmt(resume.frais_generes_ce_mois)} FCFA</div>
                  <VariationLabel pct={resume.variation_frais_generes_pct} />
                </div>
                <div className="stat-card">
                  <div style={{ fontSize: 11, color: "var(--muted)" }}>Rendement du portefeuille</div>
                  <div className="v">{resume.rendement_portefeuille_pct} %</div>
                </div>
              </div>
            </div>

            <div className="panel">
              <h2 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 12px" }}>Rapports téléchargeables</h2>
              {erreur && <div style={{ color: "var(--red)", fontSize: 12, marginBottom: 10 }}>{erreur}</div>}
              <div className="report-card">
                <div>
                  <div className="t">Rapport mensuel</div>
                  <div className="d">Synthèse complète du portefeuille, financements et remboursements</div>
                </div>
                <button className="report-dl" disabled={telechargementEnCours === "mensuel"} onClick={() => handleTelecharger("mensuel")}>
                  {telechargementEnCours === "mensuel" ? "Génération…" : "Télécharger"}
                </button>
              </div>
              <div className="report-card">
                <div>
                  <div className="t">Rapport trimestriel</div>
                  <div className="d">Vue consolidée sur 3 mois, évolution du taux de rendement</div>
                </div>
                <button className="report-dl" disabled={telechargementEnCours === "trimestriel"} onClick={() => handleTelecharger("trimestriel")}>
                  {telechargementEnCours === "trimestriel" ? "Génération…" : "Télécharger"}
                </button>
              </div>
              <div className="report-card">
                <div>
                  <div className="t">Rapport de conformité semestriel</div>
                  <div className="d">Vérification TAEG et respect des plafonds réglementaires</div>
                </div>
                <button className="report-dl" disabled={telechargementEnCours === "semestriel"} onClick={() => handleTelecharger("semestriel")}>
                  {telechargementEnCours === "semestriel" ? "Génération…" : "Télécharger"}
                </button>
              </div>
            </div>
          </>
        )}
      </main>
    </>
  );
}
