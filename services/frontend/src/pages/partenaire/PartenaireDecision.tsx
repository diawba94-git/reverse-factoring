import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { obtenirDossierDecision, approuverAvance, rejeterAvance, type DossierDecisionOut } from "../../lib/partenaireApi";
import { ApiError } from "../../lib/apiClient";

function fmt(v: string | number): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}
function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR");
}
function heuresRestantesSla(dateEmission: string): number {
  const echeanceSla = new Date(dateEmission).getTime() + 24 * 3600 * 1000;
  return Math.max(0, Math.round((echeanceSla - Date.now()) / 3600000));
}

export function PartenaireDecision() {
  const { avanceId } = useParams<{ avanceId: string }>();
  const navigate = useNavigate();
  const { session } = useAuth();
  const token = session!.accessToken;

  const [dossier, setDossier] = useState<DossierDecisionOut | null>(null);
  const [motif, setMotif] = useState("");
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    if (!avanceId) return;
    obtenirDossierDecision(avanceId, token).then(setDossier).catch(() => setDossier(null));
  }, [avanceId, token]);

  async function approuver() {
    if (!avanceId) return;
    setEnCours(true);
    setErreur(null);
    try {
      await approuverAvance(avanceId, token);
      navigate("/app/partenaire", { replace: true });
    } catch (e) {
      setErreur(e instanceof ApiError ? e.message : "Impossible d'approuver cette demande.");
    } finally {
      setEnCours(false);
    }
  }

  async function rejeter() {
    if (!avanceId) return;
    if (!motif.trim()) {
      setErreur("Un motif est obligatoire en cas de rejet.");
      return;
    }
    setEnCours(true);
    setErreur(null);
    try {
      await rejeterAvance(avanceId, motif.trim(), token);
      navigate("/app/partenaire", { replace: true });
    } catch (e) {
      setErreur(e instanceof ApiError ? e.message : "Impossible de rejeter cette demande.");
    } finally {
      setEnCours(false);
    }
  }

  if (!dossier) {
    return (
      <>
        <header className="topbar">
          <h1>Décision de financement</h1>
        </header>
        <main>Chargement…</main>
      </>
    );
  }

  const pctEnveloppe =
    dossier.enveloppe_totale && Number(dossier.enveloppe_totale) > 0
      ? ((Number(dossier.enveloppe_totale) - Number(dossier.enveloppe_disponible)) / Number(dossier.enveloppe_totale)) * 100
      : 0;

  return (
    <>
      <header className="topbar">
        <div>
          <a className="back" href="/app/partenaire">
            <svg className="ic" style={{ width: 13, height: 13 }}>
              <use href="#i-back"></use>
            </svg>{" "}
            Retour aux opportunités
          </a>
          <h1>Décision de financement</h1>
          <div className="sub">Demande soumise par {dossier.pme_raison_sociale}</div>
        </div>
        <div className="sla-tag">
          <svg className="ic" style={{ width: 14, height: 14 }}>
            <use href="#i-clock"></use>
          </svg>{" "}
          Décision attendue sous {heuresRestantesSla(dossier.avance.created_at)}h
        </div>
      </header>

      <main className="decision-main">
        <div>
          <div className="panel">
            <div className="facture-head">
              <div>
                <div className="ref mono">{dossier.numero_facture}</div>
                <div className="title">
                  {dossier.pme_raison_sociale} → {dossier.donneur_ordre_raison_sociale}
                </div>
              </div>
              <div>
                <div className="amount">{fmt(dossier.montant_ttc)}</div>
                <div className="amount-label">FCFA · échéance {dossier.duree_jours} jours</div>
              </div>
            </div>
            <div className="kv-grid">
              <div className="kv">
                <div className="l">Date d'émission</div>
                <div className="v">{fmtDate(dossier.date_emission)}</div>
              </div>
              <div className="kv">
                <div className="l">Date d'échéance</div>
                <div className="v">{fmtDate(dossier.date_echeance)}</div>
              </div>
              <div className="kv">
                <div className="l">Relation PME ↔ acheteur</div>
                <div className="v">
                  {dossier.relation_statut === "convention_signee"
                    ? "Convention signée"
                    : dossier.relation_statut === "pilote"
                      ? "Pilote"
                      : "Non renseignée"}
                </div>
              </div>
              <div className="kv">
                <div className="l">Avance demandée</div>
                <div className="v mono">{fmt(dossier.avance.montant_avance_initial)} FCFA</div>
              </div>
            </div>
          </div>

          <div className="panel">
            <h2>Vérifications</h2>
            <div className="check-list">
              <div className="check-item">
                <div className={`check-ic ${dossier.pme_statut_kyc === "valide" && dossier.donneur_ordre_statut_kyc === "valide" ? "ok" : "bad"}`}>
                  <svg className="ic">
                    <use href={`#${dossier.pme_statut_kyc === "valide" && dossier.donneur_ordre_statut_kyc === "valide" ? "i-check" : "i-x"}`}></use>
                  </svg>
                </div>
                <div className="check-txt">
                  <div className="t">KYC des deux parties</div>
                  <div className="d">
                    {dossier.pme_raison_sociale} : {dossier.pme_statut_kyc} — {dossier.donneur_ordre_raison_sociale} :{" "}
                    {dossier.donneur_ordre_statut_kyc}
                  </div>
                </div>
              </div>
              <div className="check-item">
                <div className={`check-ic ${dossier.relation_statut === "convention_signee" ? "ok" : "warn"}`}>
                  <svg className="ic">
                    <use href={`#${dossier.relation_statut === "convention_signee" ? "i-check" : "i-alert"}`}></use>
                  </svg>
                </div>
                <div className="check-txt">
                  <div className="t">Convention de domiciliation</div>
                  <div className="d">
                    {dossier.relation_statut === "convention_signee"
                      ? "Convention signée — compte dédié actif"
                      : "Relation en mode pilote — pas encore de convention complète"}
                  </div>
                </div>
              </div>
              <div className="check-item">
                <div className={`check-ic ${dossier.cheque ? "ok" : "warn"}`}>
                  <svg className="ic">
                    <use href={`#${dossier.cheque ? "i-check" : "i-alert"}`}></use>
                  </svg>
                </div>
                <div className="check-txt">
                  <div className="t">Chèque de garantie</div>
                  <div className="d">
                    {dossier.cheque
                      ? `${dossier.cheque.statut} — n° ${dossier.cheque.numero_cheque}, encaissement prévu le ${fmtDate(dossier.cheque.date_encaissement_prevue)}`
                      : "Aucun chèque déclaré pour cette facture"}
                  </div>
                </div>
              </div>
              <div className="check-item">
                <div
                  className={`check-ic ${
                    dossier.enveloppe_disponible == null || Number(dossier.enveloppe_disponible) >= Number(dossier.avance.montant_avance_initial)
                      ? "ok"
                      : "bad"
                  }`}
                >
                  <svg className="ic">
                    <use href="#i-check"></use>
                  </svg>
                </div>
                <div className="check-txt">
                  <div className="t">Enveloppe et limites de crédit</div>
                  <div className="d">
                    {dossier.enveloppe_disponible != null
                      ? `${fmt(dossier.enveloppe_disponible)} FCFA disponibles avant décision`
                      : "Aucune enveloppe configurée pour votre compte"}
                  </div>
                </div>
              </div>
              <div className="check-item">
                <div className={`check-ic ${dossier.historique_cycles_rembourses >= 3 ? "ok" : "warn"}`}>
                  <svg className="ic">
                    <use href={`#${dossier.historique_cycles_rembourses >= 3 ? "i-check" : "i-alert"}`}></use>
                  </svg>
                </div>
                <div className="check-txt">
                  <div className="t">Historique du donneur d'ordre</div>
                  <div className="d">
                    {dossier.donneur_ordre_raison_sociale} : {dossier.historique_cycles_rembourses} cycle
                    {dossier.historique_cycles_rembourses > 1 ? "s" : ""} de remboursement rapprochés à ce jour
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="panel">
            <h2>Grille tarifaire appliquée</h2>
            <div className="grille-row">
              <span>Durée</span>
              <span>{dossier.duree_jours} jours</span>
            </div>
            <div className="grille-row">
              <span>Taux total (grille)</span>
              <span>{(Number(dossier.grille_taux_total) * 100).toFixed(2).replace(".", ",")} %</span>
            </div>
            <div className="grille-row">
              <span>Commission Cedra</span>
              <span className="mono">{fmt(dossier.avance.part_plateforme)} FCFA</span>
            </div>
            <div className="grille-row">
              <span>Intérêt partenaire</span>
              <span className="mono">{fmt(dossier.avance.part_partenaire)} FCFA</span>
            </div>
            <div className="grille-row">
              <span>TAEG annualisé</span>
              <span>
                {(Number(dossier.avance.taeg_annualise) * 100).toFixed(2).replace(".", ",")} % —{" "}
                {Number(dossier.avance.taeg_annualise) <= 0.14 ? "conforme" : "à vérifier"}
              </span>
            </div>
          </div>
        </div>

        <div className="actions-panel">
          {dossier.enveloppe_totale != null && (
            <div className="panel">
              <h2>Enveloppe disponible</h2>
              <div className="envelope-bar">
                <div className="fill" style={{ width: `${Math.min(100, pctEnveloppe)}%` }}></div>
              </div>
              <div className="envelope-labels">
                <span>{fmt(Number(dossier.enveloppe_totale) - Number(dossier.enveloppe_disponible))} FCFA engagés</span>
                <span>{fmt(dossier.enveloppe_totale)} FCFA total</span>
              </div>
            </div>
          )}

          <div className="panel">
            <h2>Votre décision</h2>
            {erreur && (
              <div className="check-item" style={{ color: "var(--red)", fontSize: 12 }}>
                {erreur}
              </div>
            )}
            <button className="btn-approve" disabled={enCours} onClick={approuver}>
              Approuver le financement
            </button>
            <button className="btn-reject" disabled={enCours} onClick={rejeter}>
              Rejeter la demande
            </button>
            <div className="field">
              <label>Motif (obligatoire en cas de rejet)</label>
              <textarea
                placeholder="Ex: limite de crédit atteinte sur ce donneur d'ordre..."
                value={motif}
                onChange={(e) => setMotif(e.target.value)}
              />
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
