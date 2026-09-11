import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { usePme } from "../../context/PmeContext";
import { ErrorBanner } from "../../components/auth/ErrorBanner";
import { ApiError } from "../../lib/apiClient";
import { listerDonneursOrdre, listerFactures, type DonneurOrdreOut, type FactureOut } from "../../lib/facturesApi";
import {
  demanderAvance,
  listerEntreprisesParType,
  listerGrillesActives,
  simulerFrais,
  type EntrepriseLegereOut,
  type GrilleTarifaireOut,
  type SimulationFraisResultat,
} from "../../lib/pmeApi";

function fmt(v: string | number): string {
  return `${Number(v).toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} FCFA`;
}

export function SimulationAvance() {
  const { session } = useAuth();
  const { pmeId } = usePme();
  const token = session?.accessToken ?? "";

  const [eligibles, setEligibles] = useState<FactureOut[] | null>(null);
  const [donneurs, setDonneurs] = useState<DonneurOrdreOut[] | null>(null);
  const [grille, setGrille] = useState<GrilleTarifaireOut | null>(null);
  const [partenaires, setPartenaires] = useState<EntrepriseLegereOut[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [selectedFacture, setSelectedFacture] = useState<FactureOut | null>(null);
  const [resultat, setResultat] = useState<SimulationFraisResultat | null>(null);
  const [simError, setSimError] = useState<string | null>(null);

  const [partenaireId, setPartenaireId] = useState("");
  const [methode, setMethode] = useState<"wave" | "virement_bancaire">("virement_bancaire");
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [confirmee, setConfirmee] = useState(false);

  useEffect(() => {
    if (!pmeId || !token) return;
    listerFactures({ pme_id: pmeId, statut: "validee" }, token)
      .then(setEligibles)
      .catch(() => setLoadError("Impossible de charger les factures validées."));
    listerGrillesActives(token).then((g) => setGrille(g[0] ?? null)).catch(() => undefined);
    listerEntreprisesParType("PARTENAIRE_FINANCIER", token).then(setPartenaires).catch(() => undefined);
    listerDonneursOrdre(token).then(setDonneurs).catch(() => undefined);
  }, [pmeId, token]);

  function nomDonneur(id: string): string {
    return donneurs?.find((d) => d.id === id)?.raison_sociale ?? "…";
  }

  async function selectionnerFacture(facture: FactureOut) {
    setSelectedFacture(facture);
    setResultat(null);
    setSimError(null);
    setConfirmee(false);
    try {
      const r = await simulerFrais({ montant: facture.montant_ttc, duree_jours: facture.duree_jours }, token);
      setResultat(r);
    } catch (err) {
      setSimError(err instanceof ApiError ? err.message : "Simulation impossible pour cette facture.");
    }
  }

  async function handleConfirmer() {
    if (!selectedFacture || !partenaireId) {
      setConfirmError("Sélectionnez un partenaire financier.");
      return;
    }
    setConfirming(true);
    setConfirmError(null);
    try {
      await demanderAvance(
        { facture_id: selectedFacture.id, partenaire_financier_id: partenaireId, methode_versement: methode },
        token,
      );
      setConfirmee(true);
    } catch (err) {
      setConfirmError(err instanceof ApiError ? err.message : "Impossible de confirmer la demande.");
    } finally {
      setConfirming(false);
    }
  }

  const dureeMin = grille?.duree_minimum_jours ?? 60;
  const dureeMax = grille?.duree_maximum_jours ?? 90;
  const tauxAvance = grille ? Number(grille.taux_avance) : 0.8;
  // Le taux de frais est desormais degressif selon la duree (voir app.services.calcul_frais) :
  // pas de pourcentage fixe a lire sur la grille, on le derive du resultat de simulation
  // reel pour cette facture precise (frais_total / montant facture).
  const pourcentageFrais =
    resultat && selectedFacture ? (Number(resultat.frais_total) / Number(selectedFacture.montant_ttc)) * 100 : null;

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Demander une avance</h1>
          <div className="sub">Sélectionnez une facture validée</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        <div className="sim-panel">
          <div className="panel">
            <h2>Factures éligibles</h2>
            <div className="sub" style={{ marginBottom: 12 }}>
              Échéance comprise entre {dureeMin} et {dureeMax} jours.
            </div>

            {loadError && <ErrorBanner message={loadError} />}
            {eligibles !== null && eligibles.length === 0 && <div className="sub">Aucune facture validée pour l'instant.</div>}

            {eligibles?.map((f) => {
              const eligible = f.duree_jours >= dureeMin && f.duree_jours <= dureeMax;
              return (
                <div
                  key={f.id}
                  className={`sim-select ${selectedFacture?.id === f.id ? "selected" : ""}`}
                  style={eligible ? undefined : { opacity: 0.5, cursor: "not-allowed" }}
                  onClick={() => eligible && selectionnerFacture(f)}
                >
                  <div className="r1">
                    <span>
                      {f.numero_facture} — {nomDonneur(f.donneur_ordre_id)}
                    </span>
                    <span className="mono">{fmt(f.montant_ttc)}</span>
                  </div>
                  <div className="r2">
                    {eligible
                      ? `Validée · échéance ${f.duree_jours} jours (${new Date(f.date_echeance).toLocaleDateString("fr-FR")})`
                      : `Non éligible — échéance à ${f.duree_jours} jours, hors fenêtre ${dureeMin}-${dureeMax} jours`}
                  </div>
                </div>
              );
            })}
          </div>

          <div>
            {!selectedFacture && (
              <div className="panel">
                <div className="sub">Sélectionnez une facture éligible pour voir la simulation.</div>
              </div>
            )}

            {simError && <ErrorBanner message={simError} />}

            {selectedFacture && resultat && !confirmee && (
              <div className="panel">
                <h2>Simulation — {selectedFacture.numero_facture}</h2>
                <div className="breakdown-row">
                  <span>Montant de la facture</span>
                  <span className="mono">{fmt(selectedFacture.montant_ttc)}</span>
                </div>
                <div className="breakdown-row">
                  <span>Frais{pourcentageFrais !== null ? ` (${pourcentageFrais.toFixed(2).replace(/\.?0+$/, "")} %)` : ""}</span>
                  <span className="mono" style={{ color: "var(--red)" }}>
                    − {fmt(resultat.frais_total)}
                  </span>
                </div>
                <div className="breakdown-row">
                  <span>
                    Avance immédiate ({(tauxAvance * 100).toFixed(0)}%)
                    <span className="tag-time">Versée sous 24-48h après décision du partenaire</span>
                  </span>
                  <span className="mono">{fmt(resultat.montant_avance_initial)}</span>
                </div>
                <div className="breakdown-row">
                  <span>
                    Solde attendu ({((1 - tauxAvance) * 100).toFixed(0)}% − frais)
                    <span className="tag-time">
                      Versé après remboursement à l'échéance du {new Date(selectedFacture.date_echeance).toLocaleDateString("fr-FR")}
                    </span>
                  </span>
                  <span className="mono">{fmt(resultat.montant_solde_du)}</span>
                </div>
                <div className="breakdown-row">
                  <span>Total net à recevoir</span>
                  <span className="mono">
                    {fmt(Number(resultat.montant_avance_initial) + Number(resultat.montant_solde_du))}
                  </span>
                </div>

                <div className="warning-banner" style={{ background: "var(--green-soft)", color: "var(--green-dark)" }}>
                  Frais fixes, connus à l'avance et prélevés une seule fois, sur le solde. TAEG indicatif :{" "}
                  {(Number(resultat.taeg_annualise) * 100).toFixed(1)} %.
                </div>

                <div className="field" style={{ marginTop: 16 }}>
                  <label>Partenaire financier</label>
                  <select value={partenaireId} onChange={(e) => setPartenaireId(e.target.value)}>
                    <option value="" disabled>
                      Sélectionnez un partenaire
                    </option>
                    {partenaires?.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.raison_sociale}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="field">
                  <label>Méthode de versement</label>
                  <select value={methode} onChange={(e) => setMethode(e.target.value as "wave" | "virement_bancaire")}>
                    <option value="virement_bancaire">Virement bancaire</option>
                    <option value="wave">Wave</option>
                  </select>
                </div>

                {confirmError && <ErrorBanner message={confirmError} />}

                <button
                  type="button"
                  className="btn-primary"
                  style={{ width: "100%", marginTop: 8 }}
                  disabled={confirming}
                  onClick={handleConfirmer}
                >
                  {confirming ? "Confirmation..." : "Confirmer la demande d'avance"}
                </button>
                <div style={{ marginTop: 8, fontSize: 11.5, color: "var(--muted)", textAlign: "center" }}>
                  Aucun engagement avant confirmation.
                </div>
              </div>
            )}

            {confirmee && (
              <div className="panel" style={{ textAlign: "center", padding: "32px 20px" }}>
                <div
                  style={{
                    width: 48,
                    height: 48,
                    borderRadius: "50%",
                    background: "var(--green-soft)",
                    color: "var(--green)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 22,
                    margin: "0 auto 14px",
                  }}
                >
                  ✓
                </div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>Demande d'avance envoyée</div>
                <div className="sub" style={{ margin: "4px 0 16px" }}>
                  Suivez son avancement dans l'onglet Suivi de demande.
                </div>
                <Link to="/app/pme/suivi" className="btn-primary" style={{ textDecoration: "none" }}>
                  Voir le suivi
                </Link>
              </div>
            )}
          </div>
        </div>
      </main>
    </>
  );
}
