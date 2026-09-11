import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { apiFetch, ApiError } from "../../lib/apiClient";
import { inviterCollegue } from "../../lib/pmeApi";
import { modifierEntreprise, obtenirEntreprise } from "../../lib/entreprisesApi";
import { uploadKycDocument } from "../../lib/authApi";
import { FORME_JURIDIQUE_LABELS } from "../../lib/roles";
import type { UtilisateurOut } from "../../lib/adminApi";
import type { FormeJuridique } from "../../lib/authApi";
import { Logo } from "../../components/shell/Logo";
import "../../styles/app-tokens.css";
import "../../styles/acheteur-onboarding.css";

function rccmObligatoire(forme: FormeJuridique | ""): boolean {
  return forme !== "" && forme !== "personne_physique_entreprise_individuelle";
}

export function AcheteurOnboarding() {
  const { session, clearSession, refreshUser } = useAuth();
  const navigate = useNavigate();
  const token = session?.accessToken ?? "";

  function handleLogout() {
    clearSession();
    navigate("/login", { replace: true });
  }

  const [utilisateurs, setUtilisateurs] = useState<UtilisateurOut[] | null>(null);
  const [nomInviteur, setNomInviteur] = useState<string | null>(null);

  function recharger() {
    if (!token) return;
    apiFetch<UtilisateurOut[]>("/utilisateurs", { token }).then(setUtilisateurs).catch(() => setUtilisateurs([]));
  }
  useEffect(recharger, [token]);

  useEffect(() => {
    if (!session) return;
    obtenirEntreprise(session.user.entreprise.id, token)
      .then((e) => {
        if (e.cree_par_entreprise_id) {
          obtenirEntreprise(e.cree_par_entreprise_id, token).then((p) => setNomInviteur(p.raison_sociale)).catch(() => {});
        }
      })
      .catch(() => {});
  }, [session, token]);

  if (!session) return <Navigate to="/login" replace />;
  if (session.user.role !== "validateur_1" && session.user.role !== "validateur_2") {
    return <Navigate to="/login" replace />;
  }
  if (session.user.entreprise.statut_kyc === "valide") {
    return <Navigate to="/app/acheteur" replace />;
  }

  if (!utilisateurs) {
    return (
      <div className="cedra-app role-acheteur-onboarding">
        <div className="wrap">Chargement…</div>
      </div>
    );
  }

  const validateur1 = utilisateurs.find((u) => u.role === "validateur_1");
  const validateur2 = utilisateurs.find((u) => u.role === "validateur_2");
  const { entreprise } = session.user;

  let etape: 1 | 2 | 3 = 1;
  if (validateur2) etape = entreprise.kyc_document_url ? 3 : 2;

  return (
    <div className="cedra-app role-acheteur-onboarding">
      <div className="wrap">
        <div className="brand">
          <Logo variant="full" size={28} />
          <button type="button" className="logout-btn" onClick={handleLogout} aria-label="Se déconnecter" title="Se déconnecter">
            <svg viewBox="0 0 24 24">
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"></path>
              <polyline points="16 17 21 12 16 7"></polyline>
              <line x1="21" y1="12" x2="9" y2="12"></line>
            </svg>
          </button>
        </div>

        <div className="steps">
          <div className="step done">
            <span className="n">✓</span> Invitation acceptée
          </div>
          <div className="step-sep"></div>
          <div className={`step ${etape === 1 ? "active" : "done"}`}>
            <span className="n">{etape === 1 ? "2" : "✓"}</span> Second validateur
          </div>
          <div className="step-sep"></div>
          <div className={`step ${etape === 2 ? "active" : etape === 3 ? "done" : ""}`}>
            <span className="n">{etape > 2 ? "✓" : "3"}</span> Informations KYC
          </div>
          <div className="step-sep"></div>
          <div className={`step ${etape === 3 ? "pending" : ""}`}>
            <span className="n">{etape === 3 ? "◷" : "4"}</span> Validation admin
          </div>
        </div>

        {etape === 1 && (
          <Etape1SecondValidateur
            entrepriseId={entreprise.id}
            raisonSociale={entreprise.raison_sociale}
            nomInviteur={nomInviteur}
            validateur1Nom={validateur1?.nom ?? session.user.nom}
            token={token}
            onInvite={recharger}
          />
        )}
        {etape === 2 && (
          <Etape2Kyc
            entrepriseId={entreprise.id}
            raisonSociale={entreprise.raison_sociale}
            motifRejet={entreprise.motif_rejet_kyc}
            token={token}
            onSoumis={async () => {
              await refreshUser();
              recharger();
            }}
          />
        )}
        {etape === 3 && (
          <Etape3Attente
            raisonSociale={entreprise.raison_sociale}
            validateur1Nom={validateur1?.nom}
            validateur2Nom={validateur2?.nom}
          />
        )}
      </div>
    </div>
  );
}

function Etape1SecondValidateur({
  entrepriseId,
  raisonSociale,
  nomInviteur,
  validateur1Nom,
  token,
  onInvite,
}: {
  entrepriseId: string;
  raisonSociale: string;
  nomInviteur: string | null;
  validateur1Nom: string | null | undefined;
  token: string;
  onInvite: () => void;
}) {
  const [email, setEmail] = useState("");
  const [nom, setNom] = useState("");
  const [telephone, setTelephone] = useState("");
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  async function envoyer() {
    setErreur(null);
    if (!email.trim() || !nom.trim() || !telephone.trim()) {
      setErreur("Renseignez le nom, le téléphone et l'email du second validateur.");
      return;
    }
    setEnvoi(true);
    try {
      await inviterCollegue(
        entrepriseId,
        { telephone: telephone.trim(), email: email.trim(), nom: nom.trim(), role: "validateur_2" },
        token,
      );
      onInvite();
    } catch (e) {
      setErreur(e instanceof ApiError ? e.message : "Impossible d'envoyer l'invitation.");
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <div className="card">
      <h1>Ajoutez un second validateur</h1>
      <p className="sub">
        {raisonSociale} {nomInviteur ? `— invité par ${nomInviteur}` : ""}
      </p>

      <div className="context-box">
        <svg className="ic">
          <use href="#i-info"></use>
        </svg>
        <div>
          Chaque facture reçue sur Cedra nécessite la validation de <b>deux personnes distinctes</b> de votre entreprise.
          Vous ne pourrez pas soumettre votre dossier KYC tant qu'un second validateur n'aura pas rejoint votre compte.
        </div>
      </div>

      <div className="validator-slot">
        <div className="avatar">{(validateur1Nom ?? "V")[0]}</div>
        <div className="info">
          <b>{validateur1Nom ?? "Vous"}</b>
          <div className="role">Validateur 1 — vous</div>
        </div>
        <span className="tag-done">✓ Inscrit</span>
      </div>

      <div className="validator-slot empty">
        <div className="info" style={{ textAlign: "center", width: "100%" }}>
          <b style={{ fontSize: 12.8 }}>+ Inviter un second validateur</b>
          <div className="role">Requis avant de continuer — rôle Validateur 2</div>
        </div>
      </div>

      <div className="field" style={{ marginTop: 14 }}>
        <label>Nom du second validateur</label>
        <input type="text" placeholder="Ex: Aïda Sow" value={nom} onChange={(e) => setNom(e.target.value)} />
      </div>
      <div className="field">
        <label>Téléphone du second validateur</label>
        <input type="tel" placeholder="+221 77 000 00 00" value={telephone} onChange={(e) => setTelephone(e.target.value)} />
      </div>
      <div className="field">
        <label>Email du second validateur</label>
        <input type="email" placeholder="collegue@cfao.sn" value={email} onChange={(e) => setEmail(e.target.value)} />
        <div className="hint">Un email d'invitation lui sera envoyé pour créer son propre compte.</div>
      </div>

      {erreur && (
        <div className="error-box">
          <svg className="ic">
            <use href="#i-alert"></use>
          </svg>
          <div>{erreur}</div>
        </div>
      )}

      <div className="blocking-note">
        <svg className="ic">
          <use href="#i-alert"></use>
        </svg>
        <div>Vous pourrez continuer vers les informations KYC dès que ce second validateur aura rejoint votre compte.</div>
      </div>

      <button className="btn-primary" disabled={envoi} onClick={envoyer} style={{ marginTop: 14 }}>
        {envoi ? "Envoi…" : "Envoyer l'invitation"}
      </button>
    </div>
  );
}

function Etape2Kyc({
  entrepriseId,
  raisonSociale,
  motifRejet,
  token,
  onSoumis,
}: {
  entrepriseId: string;
  raisonSociale: string;
  motifRejet: string | null;
  token: string;
  onSoumis: () => void;
}) {
  const [formeJuridique, setFormeJuridique] = useState<FormeJuridique | "">("");
  const [ninea, setNinea] = useState("");
  const [rccm, setRccm] = useState("");
  const [adresse, setAdresse] = useState("");
  const [fichier, setFichier] = useState<File | null>(null);
  const [soumission, setSoumission] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  async function soumettre() {
    setErreur(null);
    if (!formeJuridique || !ninea.trim() || !adresse.trim() || !fichier) {
      setErreur("Renseignez la forme juridique, le NINEA, l'adresse et joignez vos documents.");
      return;
    }
    if (rccmObligatoire(formeJuridique) && !rccm.trim()) {
      setErreur("Le RCCM est obligatoire pour une société constituée.");
      return;
    }
    setSoumission(true);
    try {
      await modifierEntreprise(
        entrepriseId,
        { forme_juridique: formeJuridique, ninea: ninea.trim(), rccm: rccm.trim() || null, adresse: adresse.trim() },
        token,
      );
      await uploadKycDocument(entrepriseId, fichier, token);
      onSoumis();
    } catch (e) {
      setErreur(e instanceof ApiError ? e.message : "Impossible de soumettre le dossier KYC.");
    } finally {
      setSoumission(false);
    }
  }

  return (
    <div className="card">
      <h1>Complétez les informations de votre entreprise</h1>
      <p className="sub">{raisonSociale} — dernière étape avant l'examen par l'équipe Cedra</p>

      <div className="context-box">
        <svg className="ic">
          <use href="#i-info"></use>
        </svg>
        <div>
          Ces informations seront vérifiées par notre équipe. Le NINEA est la seule pièce obligatoire pour tous ; le RCCM
          n'est requis que pour les sociétés constituées.
        </div>
      </div>

      {motifRejet && (
        <div className="error-box">
          <svg className="ic">
            <use href="#i-alert"></use>
          </svg>
          <div>
            <b>Dossier précédemment rejeté :</b> {motifRejet}
          </div>
        </div>
      )}

      <div className="section-label">Identité de l'entreprise</div>
      <div className="field">
        <label>Forme juridique</label>
        <select value={formeJuridique} onChange={(e) => setFormeJuridique(e.target.value as FormeJuridique)}>
          <option value="" disabled>
            Sélectionnez…
          </option>
          {Object.entries(FORME_JURIDIQUE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <div className="row-2">
        <div className="field">
          <label>
            NINEA <span className="req">*</span>
          </label>
          <input type="text" placeholder="Ex: 0012345678" value={ninea} onChange={(e) => setNinea(e.target.value)} />
        </div>
        <div className="field">
          <label>RCCM {rccmObligatoire(formeJuridique) && <span className="req">*</span>}</label>
          <input type="text" placeholder="Ex: SN.DKR.2019.B.1234" value={rccm} onChange={(e) => setRccm(e.target.value)} />
        </div>
      </div>
      <div className="field">
        <label>
          Adresse <span className="req">*</span>
        </label>
        <input type="text" placeholder="Ex: Zone Industrielle, Dakar" value={adresse} onChange={(e) => setAdresse(e.target.value)} />
      </div>

      <div className="section-label">Pièces justificatives</div>
      <div className="upload-row">
        <div className="lbl">
          <svg className="ic">
            <use href="#i-file"></use>
          </svg>{" "}
          <b>Dossier KYC (NINEA, RCCM, pièce d'identité)</b> <span className="req-tag">Obligatoire</span>
        </div>
        <input type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={(e) => setFichier(e.target.files?.[0] ?? null)} style={{ maxWidth: 180 }} />
      </div>
      <div className="conditional-note">
        <svg className="ic">
          <use href="#i-info"></use>
        </svg>
        <div>Regroupez vos documents (certificat NINEA, RCCM si applicable, pièce d'identité du représentant légal) dans un seul fichier.</div>
      </div>

      {erreur && (
        <div className="error-box">
          <svg className="ic">
            <use href="#i-alert"></use>
          </svg>
          <div>{erreur}</div>
        </div>
      )}

      <button className="btn-primary" disabled={soumission} onClick={soumettre}>
        {soumission ? "Envoi…" : "Soumettre le dossier KYC"}
      </button>
    </div>
  );
}

function Etape3Attente({
  raisonSociale,
  validateur1Nom,
  validateur2Nom,
}: {
  raisonSociale: string;
  validateur1Nom: string | null | undefined;
  validateur2Nom: string | null | undefined;
}) {
  return (
    <div className="card pending-card">
      <div className="pending-ic amber">
        <svg className="ic">
          <use href="#i-clock"></use>
        </svg>
      </div>
      <h1>Votre dossier est en cours d'examen</h1>
      <p>
        L'équipe Cedra vérifie les informations et documents transmis. Vous recevrez un email dès que votre compte sera
        activé — généralement sous 24 à 48h.
      </p>

      <div className="summary">
        <div className="row">
          <span>Entreprise</span>
          <span>{raisonSociale}</span>
        </div>
        <div className="row">
          <span>Validateurs enregistrés</span>
          <span>
            {validateur1Nom ?? "—"} (V1), {validateur2Nom ?? "—"} (V2)
          </span>
        </div>
        <div className="row">
          <span>Statut</span>
          <span className="status-pill">En attente de validation</span>
        </div>
      </div>

      <div className="timeline">
        <div className="t-item">
          <span className="t-dot done"></span>
          <div>
            <div className="lbl">Invitation acceptée et compte créé</div>
          </div>
        </div>
        <div className="t-item">
          <span className="t-dot done"></span>
          <div>
            <div className="lbl">Second validateur ajouté</div>
          </div>
        </div>
        <div className="t-item">
          <span className="t-dot done"></span>
          <div>
            <div className="lbl">Dossier KYC soumis</div>
          </div>
        </div>
        <div className="t-item">
          <span className="t-dot pending"></span>
          <div>
            <div className="lbl">Vérification par l'équipe Cedra</div>
            <div className="time">En cours</div>
          </div>
        </div>
        <div className="t-item">
          <span className="t-dot pending"></span>
          <div>
            <div className="lbl">Accès complet à la plateforme</div>
            <div className="time">À venir</div>
          </div>
        </div>
      </div>

      <button className="btn-secondary">Contacter le support</button>
    </div>
  );
}
