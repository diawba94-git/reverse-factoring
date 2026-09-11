import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import "../../styles/app-tokens.css";
import "../../styles/login.css";
import { Logo } from "../../components/shell/Logo";
import { useAuth, roleHomePath } from "../../context/AuthContext";
import { login } from "../../lib/authApi";
import { ApiError } from "../../lib/apiClient";
import { isValidEmail, normalizePhone } from "../../lib/validators";
import { obtenirStatsPubliques, type PublicStatsOut } from "../../lib/publicApi";

function formatVolumeFinance(brut: string): string {
  const valeur = Number(brut);
  if (!Number.isFinite(valeur) || valeur === 0) return "0";
  if (valeur >= 1_000_000_000) return `${(valeur / 1_000_000_000).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} Md`;
  if (valeur >= 1_000_000) return `${(valeur / 1_000_000).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} M`;
  return valeur.toLocaleString("fr-FR");
}

const GENERIC_CREDENTIALS_ERROR =
  "Identifiants invalides. Vérifiez votre téléphone/email et votre mot de passe, ou réinitialisez ce dernier.";
const GENERIC_OTP_ERROR = "Code incorrect ou expiré. Vérifiez le code généré par votre application d'authentification.";

function maskIdentifiant(identifiant: string): string {
  if (isValidEmail(identifiant)) {
    const [local, domain] = identifiant.split("@");
    return local.length <= 2 ? `••@${domain}` : `${local.slice(0, 2)}••@${domain}`;
  }
  const digits = identifiant.replace(/\s+/g, "");
  if (digits.length <= 6) return digits;
  return `${digits.slice(0, 4)} •••• ${digits.slice(-2)}`;
}

function normalizeIdentifiant(value: string): string {
  const trimmed = value.trim();
  return isValidEmail(trimmed) ? trimmed : normalizePhone(trimmed);
}

export function Login() {
  const navigate = useNavigate();
  const { startSession } = useAuth();

  const [step, setStep] = useState<"credentials" | "otp">("credentials");
  const [identifiant, setIdentifiant] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [codeMfa, setCodeMfa] = useState("");
  const [showForgotHint, setShowForgotHint] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [stats, setStats] = useState<PublicStatsOut | null>(null);

  useEffect(() => {
    obtenirStatsPubliques().then(setStats).catch(() => {});
  }, []);

  async function completeLogin(access_token: string, refresh_token: string) {
    const user = await startSession({ access_token, refresh_token, token_type: "bearer" });
    // L'acheteur (validateur_1/2) suit son propre parcours d'onboarding en plusieurs
    // etapes (second validateur -> KYC -> attente admin), gere directement par la section
    // Acheteur — pas l'ecran generique PendingValidation (concu pour PME/partenaire).
    const estAcheteur = user.role === "validateur_1" || user.role === "validateur_2";
    if (user.entreprise.statut_kyc !== "valide" && !estAcheteur) {
      navigate("/pending-validation", { replace: true });
    } else {
      navigate(roleHomePath(user.role), { replace: true });
    }
  }

  async function handleCredentialsSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setFieldErrors({});

    if (!identifiant.trim() || !motDePasse) {
      setFieldErrors({
        ...(!identifiant.trim() ? { identifiant: "Champ requis" } : {}),
        ...(!motDePasse ? { mot_de_passe: "Champ requis" } : {}),
      });
      return;
    }

    setSubmitting(true);
    try {
      const result = await login({ identifiant: normalizeIdentifiant(identifiant), mot_de_passe: motDePasse });
      if (result.mfa_required) {
        setStep("otp");
      } else if (result.access_token && result.refresh_token) {
        await completeLogin(result.access_token, result.refresh_token);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("Compte désactivé. Contactez le support Cedra.");
      } else {
        setError(GENERIC_CREDENTIALS_ERROR);
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function handleOtpSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (codeMfa.length !== 6) {
      setError("Saisissez les 6 chiffres du code.");
      return;
    }

    setSubmitting(true);
    try {
      const result = await login({
        identifiant: normalizeIdentifiant(identifiant),
        mot_de_passe: motDePasse,
        code_mfa: codeMfa,
      });
      if (result.access_token && result.refresh_token) {
        await completeLogin(result.access_token, result.refresh_token);
      }
    } catch {
      setError(GENERIC_OTP_ERROR);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="cedra-app role-login">
      <div className="split">
        <div className="side">
          <div className="brand">
            <Logo variant="full" size={28} />
          </div>
          <div className="pitch">
            <h2>La facture financée avant l'échéance.</h2>
            <p>Fournisseur, acheteur ou partenaire financier — un seul compte, l'interface s'adapte automatiquement à votre rôle.</p>
            <div className="stats">
              <div><b>{stats ? stats.pme_actives : "—"}</b><span>PME actives</span></div>
              <div><b>{stats ? stats.acheteurs_actifs : "—"}</b><span>Acheteurs</span></div>
              <div><b>{stats ? formatVolumeFinance(stats.volume_finance_total) : "—"}</b><span>FCFA financés</span></div>
            </div>
          </div>
          <div className="foot">Affacturage inversé B2B · Sénégal &amp; UEMOA</div>
        </div>

        <div className="form-col">
          {step === "credentials" ? (
            <>
              <h1>Connexion</h1>
              <p className="sub">Accédez à votre espace Cedra</p>

              <div className="role-hint">
                <svg className="ic"><use href="#i-info"></use></svg>
                <div>Aucun choix de rôle à faire ici — une fois connecté, vous êtes automatiquement redirigé vers l'interface correspondant à votre compte (PME, Acheteur, Partenaire financier ou Admin).</div>
              </div>

              <form onSubmit={handleCredentialsSubmit}>
                {error && (
                  <div className="error-box">
                    <svg className="ic"><use href="#i-alert"></use></svg>
                    <div>{error}</div>
                  </div>
                )}

                <div className="field">
                  <label>Téléphone ou email</label>
                  <input
                    type="text"
                    autoComplete="username"
                    placeholder="+221 77 000 00 00 ou vous@exemple.com"
                    value={identifiant}
                    onChange={(e) => setIdentifiant(e.target.value)}
                  />
                  {fieldErrors.identifiant && (
                    <div style={{ color: "var(--red)", fontSize: 11, marginTop: 4 }}>{fieldErrors.identifiant}</div>
                  )}
                </div>
                <div className="field">
                  <div className="field-row">
                    <label style={{ marginBottom: 0 }}>Mot de passe</label>
                    <button type="button" className="forgot" onClick={() => setShowForgotHint((v) => !v)}>
                      Mot de passe oublié ?
                    </button>
                  </div>
                  <input
                    type="password"
                    autoComplete="current-password"
                    placeholder="••••••••"
                    value={motDePasse}
                    onChange={(e) => setMotDePasse(e.target.value)}
                    style={{ marginTop: 6 }}
                  />
                  {fieldErrors.mot_de_passe && (
                    <div style={{ color: "var(--red)", fontSize: 11, marginTop: 4 }}>{fieldErrors.mot_de_passe}</div>
                  )}
                </div>

                {showForgotHint && (
                  <div className="role-hint">
                    <svg className="ic"><use href="#i-info"></use></svg>
                    <div>Contactez notre équipe support pour réinitialiser votre mot de passe. La réinitialisation en libre-service arrivera dans une prochaine version.</div>
                  </div>
                )}

                <button type="submit" className="btn-primary" disabled={submitting}>
                  {submitting ? "Connexion..." : "Se connecter"}
                </button>
              </form>

              <div className="signup-row">
                Pas encore de compte ? <Link to="/register">Créer un compte</Link>
              </div>
            </>
          ) : (
            <>
              <h1>Vérification en deux étapes</h1>
              <p className="sub">
                Saisissez le code à 6 chiffres généré par votre application d'authentification pour le compte {maskIdentifiant(identifiant)}.
              </p>

              <form onSubmit={handleOtpSubmit}>
                {error && (
                  <div className="error-box">
                    <svg className="ic"><use href="#i-alert"></use></svg>
                    <div>{error}</div>
                  </div>
                )}

                <div className="field">
                  <label>Code de vérification</label>
                  <input
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    placeholder="000000"
                    value={codeMfa}
                    onChange={(e) => setCodeMfa(e.target.value.replace(/[^0-9]/g, "").slice(0, 6))}
                    autoFocus
                    style={{ letterSpacing: "0.3em", fontFamily: "'IBM Plex Mono', monospace" }}
                  />
                </div>

                <button type="submit" className="btn-primary" disabled={submitting}>
                  {submitting ? "Vérification..." : "Vérifier et continuer"}
                </button>
              </form>

              <div className="signup-row">
                <button
                  type="button"
                  className="link-button"
                  onClick={() => {
                    setStep("credentials");
                    setCodeMfa("");
                    setError(null);
                  }}
                >
                  Retour
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
