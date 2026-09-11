import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { rejoindreEntreprise } from "../../lib/entreprisesApi";
import { ApiError } from "../../lib/apiClient";
import { Logo } from "../../components/shell/Logo";
import "../../styles/app-tokens.css";
import "../../styles/acheteur-onboarding.css";

export function AcheteurRejoindre() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { startSession } = useAuth();

  const [nom, setNom] = useState("");
  const [telephone, setTelephone] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [soumission, setSoumission] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setErreur(null);
    if (!nom.trim() || !telephone.trim() || motDePasse.length < 8) {
      setErreur("Renseignez votre nom, votre téléphone et un mot de passe d'au moins 8 caractères.");
      return;
    }
    setSoumission(true);
    try {
      const tokens = await rejoindreEntreprise(token, { nom: nom.trim(), telephone: telephone.trim(), mot_de_passe: motDePasse });
      await startSession(tokens);
      navigate("/app/acheteur/onboarding", { replace: true });
    } catch (e) {
      setErreur(e instanceof ApiError ? e.message : "Ce lien d'invitation est introuvable ou a déjà été utilisé.");
    } finally {
      setSoumission(false);
    }
  }

  return (
    <div className="cedra-app role-acheteur-onboarding">
      <div className="wrap">
        <div className="brand">
          <Logo variant="full" size={28} />
        </div>
        <div className="card">
          <h1>Rejoindre votre entreprise sur Cedra</h1>
          <p className="sub">Créez votre compte pour devenir le premier validateur de votre entreprise.</p>

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label>Nom complet</label>
              <input type="text" value={nom} onChange={(e) => setNom(e.target.value)} />
            </div>
            <div className="field">
              <label>Téléphone</label>
              <input type="tel" placeholder="+221 77 000 00 00" value={telephone} onChange={(e) => setTelephone(e.target.value)} />
            </div>
            <div className="field">
              <label>Mot de passe</label>
              <input type="password" value={motDePasse} onChange={(e) => setMotDePasse(e.target.value)} />
            </div>

            {erreur && (
              <div className="error-box">
                <svg className="ic">
                  <use href="#i-alert"></use>
                </svg>
                <div>{erreur}</div>
              </div>
            )}

            <button type="submit" className="btn-primary" disabled={soumission}>
              {soumission ? "Création…" : "Créer mon compte"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
