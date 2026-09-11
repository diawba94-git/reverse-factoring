import { Fragment, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { usePme } from "../../context/PmeContext";
import { PmeGate } from "./PmeSection";
import { BASE_URL, ApiError } from "../../lib/apiClient";
import { creerFicheMinimale } from "../../lib/entreprisesApi";
import { declarerCheque } from "../../lib/chequeApi";
import {
  creerFactureNative,
  extraireFacturePourCreation,
  listerDonneursOrdre,
  transmettreFacture,
  type DonneurOrdreOut,
  type FactureOut,
} from "../../lib/facturesApi";
import type { FicheMinimaleOut } from "../../lib/entreprisesApi";

type LigneForm = { clientId: string; designation: string; description: string; quantite: string; prixUnitaire: string };

function ligneVide(): LigneForm {
  return { clientId: crypto.randomUUID(), designation: "", description: "", quantite: "1", prixUnitaire: "" };
}
function toNumber(v: string): number {
  const n = Number(v.replace(",", "."));
  return Number.isFinite(n) ? n : 0;
}
function fmt(n: number): string {
  return n.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}
function dansNJours(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

type DonneurSelectionne = {
  id: string;
  raison_sociale: string;
  statut_fiche: "pre_inscrite" | "active";
  tokenInvitation?: string | null;
};

function StepsHeader({ step }: { step: 1 | 2 | 3 | 4 }) {
  const labels = ["Informations facture", "Acheteur", "Lignes & totaux", "Validation"];
  return (
    <div className="steps">
      {labels.map((label, i) => {
        const n = (i + 1) as 1 | 2 | 3 | 4;
        const done = n < step;
        const active = n === step;
        return (
          <Fragment key={label}>
            <div className={`step ${done ? "done" : ""} ${active ? "active" : ""}`}>
              <span className="n">{done ? "✓" : n}</span> {label}
            </div>
            {i < labels.length - 1 && <div className="step-sep"></div>}
          </Fragment>
        );
      })}
    </div>
  );
}

function PmeCreerFactureContent() {
  const { session } = useAuth();
  const { pmeId } = usePme();
  const navigate = useNavigate();
  const token = session!.accessToken;

  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);

  // Step 1
  const [dateEmission, setDateEmission] = useState(todayIso());
  const [dateEcheance, setDateEcheance] = useState(dansNJours(60));
  const [tauxTva, setTauxTva] = useState("18");
  const [notes, setNotes] = useState("");
  const [ocrEnCours, setOcrEnCours] = useState(false);
  const [ocrErreur, setOcrErreur] = useState<string | null>(null);
  const [ocrAvertissements, setOcrAvertissements] = useState<string[]>([]);
  const [ocrApplique, setOcrApplique] = useState(false);

  // Step 2
  const [donneurs, setDonneurs] = useState<DonneurOrdreOut[]>([]);
  const [recherche, setRecherche] = useState("");
  const [selection, setSelection] = useState<DonneurSelectionne | null>(null);
  const [ficheNom, setFicheNom] = useState("");
  const [ficheContactNom, setFicheContactNom] = useState("");
  const [ficheContactEmail, setFicheContactEmail] = useState("");
  const [creationFicheEnCours, setCreationFicheEnCours] = useState(false);
  const [chequeOn, setChequeOn] = useState(false);
  const [chequeNumero, setChequeNumero] = useState("");
  const [chequeBanque, setChequeBanque] = useState("");
  const [chequeDate, setChequeDate] = useState("");
  const [chequeFichier, setChequeFichier] = useState<File | null>(null);

  useEffect(() => {
    listerDonneursOrdre(token).then(setDonneurs).catch(() => {});
  }, [token]);
  useEffect(() => {
    setFicheNom(recherche);
  }, [recherche]);
  useEffect(() => {
    if (!chequeDate && dateEcheance) setChequeDate(dateEcheance);
  }, [dateEcheance, chequeDate]);

  const resultats = recherche.trim()
    ? donneurs.filter((d) => d.raison_sociale.toLowerCase().includes(recherche.trim().toLowerCase()))
    : [];

  // Step 3
  const [lignes, setLignes] = useState<LigneForm[]>([ligneVide()]);

  async function handleImportFichier(fichier: File | null) {
    if (!fichier) return;
    setOcrEnCours(true);
    setOcrErreur(null);
    setOcrAvertissements([]);
    setOcrApplique(false);
    try {
      const extraction = await extraireFacturePourCreation(fichier, token);
      if (extraction.date_emission) setDateEmission(extraction.date_emission);
      if (extraction.date_echeance) setDateEcheance(extraction.date_echeance);
      if (extraction.taux_tva) setTauxTva((Number(extraction.taux_tva) * 100).toString());
      if (extraction.lignes.length > 0) {
        setLignes(
          extraction.lignes.map((l) => ({
            clientId: crypto.randomUUID(),
            designation: l.designation,
            description: "",
            quantite: l.quantite,
            prixUnitaire: l.prix_unitaire,
          })),
        );
      }
      setOcrAvertissements(extraction.avertissements);
      setOcrApplique(true);
    } catch (e) {
      setOcrErreur(e instanceof ApiError ? e.message : "L'analyse du document a échoué. Remplissez le formulaire manuellement.");
    } finally {
      setOcrEnCours(false);
    }
  }

  // Step 4 / soumission
  const [erreur, setErreur] = useState<string | null>(null);
  const [soumission, setSoumission] = useState(false);
  const [factureCreee, setFactureCreee] = useState<FactureOut | null>(null);
  const [transmissionEnCours, setTransmissionEnCours] = useState(false);

  async function creerFiche() {
    setErreur(null);
    if (!ficheNom.trim() || !ficheContactNom.trim() || !ficheContactEmail.trim()) {
      setErreur("Renseignez le nom de la société, le contact et son email.");
      return;
    }
    setCreationFicheEnCours(true);
    try {
      const fiche: FicheMinimaleOut = await creerFicheMinimale(
        { raison_sociale: ficheNom.trim(), contact_invitation_nom: ficheContactNom.trim(), contact_invitation_email: ficheContactEmail.trim() },
        token,
      );
      setSelection({
        id: fiche.id,
        raison_sociale: fiche.raison_sociale,
        statut_fiche: fiche.statut_fiche,
        tokenInvitation: fiche.token_invitation,
      });
    } catch (e) {
      setErreur(e instanceof ApiError ? e.message : "Impossible de créer la fiche acheteur.");
    } finally {
      setCreationFicheEnCours(false);
    }
  }

  const totauxLignes = lignes.map((l) => toNumber(l.quantite) * toNumber(l.prixUnitaire));
  const sousTotal = totauxLignes.reduce((a, v) => a + v, 0);
  const montantTva = sousTotal * (toNumber(tauxTva) / 100);
  const totalGeneral = sousTotal + montantTva;

  async function soumettreFacture() {
    if (!selection) return;
    setErreur(null);
    setSoumission(true);
    try {
      const facture = await creerFactureNative(
        {
          donneur_ordre_id: selection.id,
          date_emission: dateEmission,
          date_echeance: dateEcheance,
          taux_tva: (toNumber(tauxTva) / 100).toFixed(4),
          notes: notes.trim() || null,
          lignes: lignes.map((l) => ({
            designation: l.designation.trim(),
            description: l.description.trim() || null,
            quantite: l.quantite,
            prix_unitaire: l.prixUnitaire,
          })),
          pme_id: pmeId ?? undefined,
        },
        token,
      );

      if (chequeOn && chequeNumero.trim() && chequeBanque.trim() && chequeDate && chequeFichier) {
        try {
          await declarerCheque(
            facture.id,
            { numeroCheque: chequeNumero.trim(), banqueEmettrice: chequeBanque.trim(), dateEncaissementPrevue: chequeDate, fichier: chequeFichier },
            token,
          );
        } catch {
          // La facture existe deja ; on ne bloque pas sa creation pour un echec de declaration
          // de cheque (optionnel), mais on garde une trace visible.
          setErreur("La facture a été créée mais la déclaration du chèque a échoué. Vous pourrez réessayer depuis le suivi de la facture.");
        }
      }

      setFactureCreee(facture);
    } catch (e) {
      setErreur(e instanceof ApiError ? e.message : "Une erreur est survenue. Réessayez.");
    } finally {
      setSoumission(false);
    }
  }

  async function transmettre() {
    if (!factureCreee) return;
    setTransmissionEnCours(true);
    try {
      await transmettreFacture(factureCreee.id, token);
      navigate("/app/pme/factures");
    } catch (e) {
      setErreur(e instanceof ApiError ? e.message : "Une erreur est survenue. Réessayez.");
      setTransmissionEnCours(false);
    }
  }

  if (factureCreee) {
    return (
      <>
        <header className="topbar">
          <div>
            <h1>Créer une facture</h1>
          </div>
        </header>
        <main className="creer-facture-main">
          <div className="panel">
            <h2>{factureCreee.statut === "brouillon" ? "Facture prête à être transmise" : `Facture ${factureCreee.numero_facture} transmise`}</h2>
            <p className="sub">
              {factureCreee.statut === "en_attente_kyc_acheteur"
                ? "Statut : en attente KYC acheteur — elle passera automatiquement à « Émise » dès que l'acheteur aura complété son inscription."
                : `Statut : ${factureCreee.statut} — Montant TTC : ${fmt(Number(factureCreee.montant_ttc))} ${factureCreee.devise}`}
            </p>
            <iframe
              title="Aperçu de la facture"
              src={`${BASE_URL}${factureCreee.piece_justificative_url}`}
              style={{ width: "100%", height: 420, border: "1px solid var(--line)", borderRadius: 8 }}
            />
            {erreur && (
              <div className="warning-banner" style={{ marginTop: 12 }}>
                {erreur}
              </div>
            )}
            <div className="actions">
              {factureCreee.statut === "brouillon" && (
                <button className="btn-primary" disabled={transmissionEnCours} onClick={transmettre}>
                  {transmissionEnCours ? "Transmission…" : "Transmettre au donneur d'ordre"}
                </button>
              )}
            </div>
          </div>
        </main>
      </>
    );
  }

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Créer une facture</h1>
        </div>
      </header>
      <main className="creer-facture-main">
        <StepsHeader step={step} />

        {step === 1 && (
          <>
            <div className="panel">
              <h2>Importer une facture existante (optionnel)</h2>
              <p className="sub">
                Gagnez du temps : importez un PDF ou une photo de la facture déjà émise, nous pré-remplirons les champs
                ci-dessous à partir de son contenu — vérifiez-les avant de continuer.
              </p>
              <div className="field">
                <label>Fichier (PDF, photo ou scan)</label>
                <input
                  type="file"
                  accept="application/pdf,image/*"
                  disabled={ocrEnCours}
                  onChange={(e) => handleImportFichier(e.target.files?.[0] ?? null)}
                />
              </div>
              {ocrEnCours && <div className="hint">Analyse du document en cours…</div>}
              {ocrErreur && (
                <div className="warning-banner">
                  <svg className="ic">
                    <use href="#i-alert"></use>
                  </svg>
                  <div>{ocrErreur}</div>
                </div>
              )}
              {ocrApplique && (
                <div className="hint">
                  <svg className="ic" style={{ width: 12, height: 12 }}>
                    <use href="#i-info"></use>
                  </svg>{" "}
                  Champs pré-remplis à partir du document importé — relisez-les avant de continuer.
                  {ocrAvertissements.map((a, i) => (
                    <div key={i}>{a}</div>
                  ))}
                </div>
              )}
            </div>

            <div className="panel">
            <h2>Informations de la facture</h2>
            <p className="sub">Dates et taux applicables. Le numéro est attribué automatiquement à la transmission.</p>
            <div className="row-2">
              <div className="field">
                <label>Date de facture</label>
                <input type="date" value={dateEmission} onChange={(e) => setDateEmission(e.target.value)} />
              </div>
              <div className="field">
                <label>Date d'échéance</label>
                <input type="date" value={dateEcheance} onChange={(e) => setDateEcheance(e.target.value)} />
                <div className="hint">Fenêtre éligible : 60 à 90 jours.</div>
              </div>
            </div>
            <div className="field" style={{ maxWidth: 160 }}>
              <label>Taux de TVA (%)</label>
              <input type="number" min="0" step="0.01" value={tauxTva} onChange={(e) => setTauxTva(e.target.value)} />
            </div>
            <div className="field">
              <label>Notes (optionnel)</label>
              <textarea style={{ minHeight: 70 }} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Modalités de paiement, notes libres..." />
            </div>
            <div className="actions">
              <button className="btn-primary" onClick={() => setStep(2)}>
                Continuer — Acheteur
              </button>
            </div>
            </div>
          </>
        )}

        {step === 2 && (
          <>
            {!selection ? (
              <>
                <div className="panel">
                  <h2>À qui adressez-vous cette facture ?</h2>
                  <p className="sub">Recherchez un acheteur déjà présent sur Cedra avant d'en créer un nouveau.</p>
                  <div className="field">
                    <label>Rechercher un acheteur</label>
                    <input
                      type="text"
                      placeholder="Nom de la société (ex: Auchan Sénégal, Sonatel...)"
                      value={recherche}
                      onChange={(e) => setRecherche(e.target.value)}
                    />
                  </div>

                  {recherche.trim() && resultats.length > 0 && (
                    <>
                      {resultats.map((d) => (
                        <div className="search-result" key={d.id}>
                          <div>
                            <div className="name">{d.raison_sociale}</div>
                          </div>
                          <button
                            className="pick"
                            onClick={() => setSelection({ id: d.id, raison_sociale: d.raison_sociale, statut_fiche: "active" })}
                          >
                            Choisir
                          </button>
                        </div>
                      ))}
                    </>
                  )}

                  {recherche.trim() && resultats.length === 0 && (
                    <div className="empty-search">
                      <svg className="ic">
                        <use href="#i-info"></use>
                      </svg>
                      <div>
                        <b>Aucun résultat pour « {recherche.trim()} ».</b>
                        <br />
                        Cet acheteur n'est pas encore inscrit sur Cedra — vous pouvez créer sa fiche ci-dessous. Une invitation lui
                        sera envoyée par email pour compléter ses informations.
                      </div>
                    </div>
                  )}
                </div>

                {recherche.trim() && resultats.length === 0 && (
                  <div className="panel">
                    <h2>Créer la fiche acheteur</h2>
                    <p className="sub">
                      Seules ces informations minimales sont nécessaires — l'acheteur complétera lui-même le reste (NINEA,
                      adresse, KYC).
                    </p>
                    <div className="field">
                      <label>Nom de la société</label>
                      <input type="text" value={ficheNom} onChange={(e) => setFicheNom(e.target.value)} />
                    </div>
                    <div className="row-2">
                      <div className="field">
                        <label>Nom du contact</label>
                        <input type="text" placeholder="Ex: Moussa Ndiaye" value={ficheContactNom} onChange={(e) => setFicheContactNom(e.target.value)} />
                      </div>
                      <div className="field">
                        <label>Email du contact</label>
                        <input
                          type="email"
                          placeholder="moussa.ndiaye@cfao.sn"
                          value={ficheContactEmail}
                          onChange={(e) => setFicheContactEmail(e.target.value)}
                        />
                        <div className="hint">Une invitation sera envoyée à cette adresse pour compléter la fiche de l'entreprise.</div>
                      </div>
                    </div>
                    {erreur && (
                      <div className="warning-banner">
                        <svg className="ic">
                          <use href="#i-alert"></use>
                        </svg>
                        <div>{erreur}</div>
                      </div>
                    )}
                    <div className="actions">
                      <button className="btn-primary" disabled={creationFicheEnCours} onClick={creerFiche}>
                        {creationFicheEnCours ? "Création…" : "Créer la fiche acheteur"}
                      </button>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="panel">
                <h2>Acheteur sélectionné</h2>
                <div className="acheteur-selected">
                  <div>
                    <div className="name">{selection.raison_sociale}</div>
                    {selection.statut_fiche === "pre_inscrite" && <div className="tag">Fiche nouvellement créée — en attente d'inscription</div>}
                  </div>
                  <button className="change-btn" onClick={() => setSelection(null)}>
                    Changer
                  </button>
                </div>

                {selection.tokenInvitation && (
                  <div className="hint" style={{ marginTop: 8 }}>
                    Aucun envoi d'email automatique dans cette version — transmettez ce lien d'inscription vous-même au
                    contact invité :{" "}
                    <span className="mono" style={{ wordBreak: "break-all" }}>
                      {window.location.origin}/rejoindre/{selection.tokenInvitation}
                    </span>
                  </div>
                )}

                <div className="toggle-row" style={{ paddingTop: 18 }}>
                  <div>
                    <div className="lbl">L'acheteur vous a déjà remis un chèque pour cette facture ?</div>
                    <div className="desc">
                      Optionnel. Si vous détenez déjà un chèque post-daté remis par l'acheteur, déclarez-le : il pourra servir de
                      garantie auprès du partenaire financier une fois confirmé.
                    </div>
                  </div>
                  <button className={`switch ${chequeOn ? "on" : ""}`} onClick={() => setChequeOn((v) => !v)} aria-label="Activer la déclaration de chèque">
                    <div className="knob"></div>
                  </button>
                </div>

                {chequeOn && (
                  <div className="cheque-block">
                    <div className="row-2">
                      <div className="field">
                        <label>Numéro du chèque</label>
                        <input type="text" placeholder="Ex: 0041235" value={chequeNumero} onChange={(e) => setChequeNumero(e.target.value)} />
                      </div>
                      <div className="field">
                        <label>Banque émettrice</label>
                        <input type="text" placeholder="Ex: Banque Atlantique Sénégal" value={chequeBanque} onChange={(e) => setChequeBanque(e.target.value)} />
                      </div>
                    </div>
                    <div className="row-2">
                      <div className="field">
                        <label>Date d'encaissement prévue</label>
                        <input type="date" value={chequeDate} onChange={(e) => setChequeDate(e.target.value)} />
                      </div>
                      <div className="field">
                        <label>Photo / scan du chèque</label>
                        <input type="file" accept="image/*,.pdf" onChange={(e) => setChequeFichier(e.target.files?.[0] ?? null)} />
                      </div>
                    </div>
                    <div className="hint">
                      <svg className="ic" style={{ width: 12, height: 12 }}>
                        <use href="#i-info"></use>
                      </svg>{" "}
                      Ce chèque devra être confirmé par l'acheteur lui-même avant d'être considéré comme une garantie fiable par
                      le partenaire financier.
                    </div>
                  </div>
                )}

                {selection.statut_fiche === "pre_inscrite" && (
                  <div className="warning-banner">
                    <svg className="ic">
                      <use href="#i-alert"></use>
                    </svg>
                    <div>
                      <b>Cette facture sera créée avec le statut « En attente KYC acheteur ».</b>
                      <br />
                      Comme {selection.raison_sociale} n'est pas encore inscrit sur Cedra, la facture ne pourra pas être validée
                      ni financée tant que son inscription et son KYC ne seront pas complétés. Elle passera automatiquement au
                      statut « Émise » dès que ce sera fait — vous n'aurez rien à refaire.
                    </div>
                  </div>
                )}

                <div className="actions">
                  <button className="btn-secondary" onClick={() => setStep(1)}>
                    Retour
                  </button>
                  <button className="btn-primary" onClick={() => setStep(3)}>
                    Continuer — Lignes &amp; totaux
                  </button>
                </div>
              </div>
            )}
          </>
        )}

        {step === 3 && (
          <div className="panel">
            <h2>Détails des articles</h2>
            <p className="sub">Ajoutez une ligne par article ou prestation facturé(e).</p>
            {lignes.map((ligne, i) => (
              <div key={ligne.clientId} style={{ borderTop: i > 0 ? "1px solid var(--line)" : undefined, paddingTop: i > 0 ? 12 : 0, marginTop: i > 0 ? 12 : 0 }}>
                <div className="row-2">
                  <div className="field">
                    <label>Désignation</label>
                    <input
                      type="text"
                      value={ligne.designation}
                      onChange={(e) => setLignes((prev) => prev.map((l) => (l.clientId === ligne.clientId ? { ...l, designation: e.target.value } : l)))}
                      placeholder="Nom de l'article"
                    />
                  </div>
                  <div className="field">
                    <label>Description (optionnel)</label>
                    <input
                      type="text"
                      value={ligne.description}
                      onChange={(e) => setLignes((prev) => prev.map((l) => (l.clientId === ligne.clientId ? { ...l, description: e.target.value } : l)))}
                    />
                  </div>
                </div>
                <div className="row-2">
                  <div className="field">
                    <label>Quantité</label>
                    <input
                      type="number"
                      min="0"
                      value={ligne.quantite}
                      onChange={(e) => setLignes((prev) => prev.map((l) => (l.clientId === ligne.clientId ? { ...l, quantite: e.target.value } : l)))}
                    />
                  </div>
                  <div className="field">
                    <label>Prix unitaire</label>
                    <input
                      type="number"
                      min="0"
                      value={ligne.prixUnitaire}
                      onChange={(e) => setLignes((prev) => prev.map((l) => (l.clientId === ligne.clientId ? { ...l, prixUnitaire: e.target.value } : l)))}
                    />
                  </div>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5, color: "var(--muted)" }}>
                  <button
                    className="change-btn"
                    disabled={lignes.length === 1}
                    onClick={() => setLignes((prev) => prev.filter((l) => l.clientId !== ligne.clientId))}
                  >
                    Supprimer cette ligne
                  </button>
                  <span>Total : {fmt(toNumber(ligne.quantite) * toNumber(ligne.prixUnitaire))} FCFA</span>
                </div>
              </div>
            ))}
            <div className="actions" style={{ justifyContent: "flex-start", marginTop: 14 }}>
              <button className="btn-secondary" onClick={() => setLignes((prev) => [...prev, ligneVide()])}>
                + Ajouter un article
              </button>
            </div>

            <div style={{ borderTop: "1px solid var(--line)", marginTop: 16, paddingTop: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <span>Sous-total (HT)</span>
                <span className="mono">{fmt(sousTotal)} FCFA</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginTop: 6 }}>
                <span>TVA ({tauxTva}%)</span>
                <span className="mono">{fmt(montantTva)} FCFA</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 14, fontWeight: 700, marginTop: 8 }}>
                <span>Total général</span>
                <span className="mono">{fmt(totalGeneral)} FCFA</span>
              </div>
            </div>

            <div className="actions">
              <button className="btn-secondary" onClick={() => setStep(2)}>
                Retour
              </button>
              <button className="btn-primary" onClick={() => setStep(4)}>
                Continuer — Validation
              </button>
            </div>
          </div>
        )}

        {step === 4 && selection && (
          <div className="panel">
            <h2>Récapitulatif</h2>
            <p className="sub">Vérifiez les informations avant de créer la facture.</p>
            <div style={{ fontSize: 13, lineHeight: 1.9 }}>
              <div>
                <b>Acheteur :</b> {selection.raison_sociale}
              </div>
              <div>
                <b>Émission :</b> {dateEmission} — <b>Échéance :</b> {dateEcheance}
              </div>
              <div>
                <b>Lignes :</b> {lignes.length} article{lignes.length > 1 ? "s" : ""}
              </div>
              <div>
                <b>Total TTC :</b> {fmt(totalGeneral)} FCFA
              </div>
              {chequeOn && (
                <div>
                  <b>Chèque déclaré :</b> {chequeNumero || "—"} ({chequeBanque || "—"})
                </div>
              )}
            </div>

            {erreur && (
              <div className="warning-banner">
                <svg className="ic">
                  <use href="#i-alert"></use>
                </svg>
                <div>{erreur}</div>
              </div>
            )}

            <div className="actions">
              <button className="btn-secondary" onClick={() => setStep(3)}>
                Retour
              </button>
              <button className="btn-primary" disabled={soumission} onClick={soumettreFacture}>
                {soumission ? "Création…" : "Créer la facture"}
              </button>
            </div>
          </div>
        )}
      </main>
    </>
  );
}

export function PmeCreerFacture() {
  return (
    <PmeGate>
      <PmeCreerFactureContent />
    </PmeGate>
  );
}
