import { useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthLayout } from "./AuthLayout";
import { FormField } from "../../components/auth/FormField";
import { ErrorBanner } from "../../components/auth/ErrorBanner";
import { AccountTypeCard } from "../../components/auth/AccountTypeCard";
import { ApiError } from "../../lib/apiClient";
import { isValidEmail, isValidNinea, isValidPhone, normalizePhone } from "../../lib/validators";
import {
  me as fetchMe,
  registerEntreprise,
  uploadKycDocument,
  type FormeJuridique,
  type MeResponse,
  type TypeEntreprise,
} from "../../lib/authApi";
import { FORME_JURIDIQUE_LABELS } from "../../lib/roles";

const FORMES_JURIDIQUES = Object.entries(FORME_JURIDIQUE_LABELS) as [FormeJuridique, string][];

function rccmEstObligatoire(forme: FormeJuridique | null): boolean {
  return forme !== null && forme !== "personne_physique_entreprise_individuelle";
}

const ACCOUNT_TYPES: { value: TypeEntreprise; label: string; description: string }[] = [
  {
    value: "PME",
    label: "PME fournisseur",
    description: "Vous émettez des factures et demandez des avances de trésorerie.",
  },
  {
    value: "GRANDE_ENTREPRISE",
    label: "Grande entreprise (donneur d'ordre)",
    description: "Vous validez les factures émises par vos fournisseurs.",
  },
  {
    value: "PARTENAIRE_FINANCIER",
    label: "Partenaire financier",
    description: "Vous financez les avances sur factures validées.",
  },
];

type FormState = {
  type: TypeEntreprise | null;
  raisonSociale: string;
  ninea: string;
  formeJuridique: FormeJuridique | null;
  rccm: string;
  secteurActivite: string;
  adresse: string;
  telephone: string;
  email: string;
  motDePasse: string;
  confirmation: string;
};

const EMPTY_FORM: FormState = {
  type: null,
  raisonSociale: "",
  ninea: "",
  formeJuridique: null,
  rccm: "",
  secteurActivite: "",
  adresse: "",
  telephone: "",
  email: "",
  motDePasse: "",
  confirmation: "",
};

const BACKEND_FIELD_MAP: Record<string, keyof FormState> = {
  type: "type",
  raison_sociale: "raisonSociale",
  ninea: "ninea",
  forme_juridique: "formeJuridique",
  rccm: "rccm",
  secteur_activite: "secteurActivite",
  adresse: "adresse",
  telephone: "telephone",
  email: "email",
  mot_de_passe: "motDePasse",
};

export function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<keyof FormState, string>>>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [createdAccessToken, setCreatedAccessToken] = useState<string | null>(null);
  const [createdUser, setCreatedUser] = useState<MeResponse | null>(null);

  function setField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function validate(): Partial<Record<keyof FormState, string>> {
    const errors: Partial<Record<keyof FormState, string>> = {};
    if (!form.type) errors.type = "Sélectionnez un type de compte";
    if (!form.raisonSociale.trim()) errors.raisonSociale = "Champ requis";
    if (!isValidNinea(form.ninea)) {
      errors.ninea = "Format attendu : 9 chiffres (ex. 005912345), suivis éventuellement d'un code régime de 3 caractères";
    }
    if (!form.formeJuridique) errors.formeJuridique = "Sélectionnez une forme juridique";
    if (rccmEstObligatoire(form.formeJuridique) && !form.rccm.trim()) {
      errors.rccm = "Le RCCM est obligatoire pour cette forme juridique";
    }
    if (!form.secteurActivite.trim()) errors.secteurActivite = "Champ requis";
    if (!form.adresse.trim()) errors.adresse = "Champ requis";
    if (!isValidPhone(form.telephone)) errors.telephone = "Numéro de téléphone invalide";
    if (!isValidEmail(form.email)) errors.email = "Adresse e-mail invalide";
    if (form.motDePasse.length < 8) errors.motDePasse = "8 caractères minimum";
    if (form.confirmation !== form.motDePasse) errors.confirmation = "Les mots de passe ne correspondent pas";
    return errors;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const errors = validate();
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    try {
      const tokens = await registerEntreprise({
        type: form.type as TypeEntreprise,
        raison_sociale: form.raisonSociale.trim(),
        ninea: form.ninea.trim(),
        forme_juridique: form.formeJuridique as FormeJuridique,
        rccm: form.rccm.trim() || undefined,
        secteur_activite: form.secteurActivite.trim(),
        adresse: form.adresse.trim(),
        telephone: normalizePhone(form.telephone),
        email: form.email.trim(),
        mot_de_passe: form.motDePasse,
      });
      const user = await fetchMe(tokens.access_token);
      setCreatedAccessToken(tokens.access_token);
      setCreatedUser(user);
    } catch (err) {
      if (err instanceof ApiError) {
        const mapped: Partial<Record<keyof FormState, string>> = {};
        for (const [backendField, msg] of Object.entries(err.fieldErrors)) {
          const key = BACKEND_FIELD_MAP[backendField];
          if (key) mapped[key] = msg;
        }
        if (Object.keys(mapped).length > 0) {
          setFieldErrors(mapped);
        } else if (err.status === 409 && err.message.toLowerCase().includes("ninea")) {
          setFieldErrors({ ninea: err.message });
        } else if (err.status === 409 && err.message.toLowerCase().includes("telephone")) {
          setFieldErrors({ telephone: err.message });
        } else {
          setError(err.message);
        }
      } else {
        setError("Une erreur est survenue. Réessayez.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (createdUser && createdAccessToken) {
    return (
      <ConfirmationScreen
        user={createdUser}
        accessToken={createdAccessToken}
        onDone={() => navigate("/login", { replace: true })}
      />
    );
  }

  return (
    <AuthLayout>
      <div className="auth-card">
        <div className="auth-card-title">Créer un compte</div>
        <div className="auth-card-subtitle">
          Renseignez les informations de votre entreprise pour rejoindre Cedra.
        </div>

        <form onSubmit={handleSubmit}>
          <div className="auth-field" style={{ marginTop: 24 }}>
            <span className="auth-label">Vous êtes...</span>
            <div className="auth-account-type-group">
              {ACCOUNT_TYPES.map((option) => (
                <AccountTypeCard
                  key={option.value}
                  label={option.label}
                  description={option.description}
                  selected={form.type === option.value}
                  onSelect={() => setField("type", option.value)}
                />
              ))}
            </div>
            {fieldErrors.type && <span className="auth-field-error">{fieldErrors.type}</span>}
          </div>

          <FormField
            label="Raison sociale de l'entreprise"
            placeholder="Ex : Senegal Fruits SARL"
            value={form.raisonSociale}
            onChange={(e) => setField("raisonSociale", e.target.value)}
            error={fieldErrors.raisonSociale}
          />

          <FormField
            label="NINEA"
            placeholder="005912345"
            value={form.ninea}
            onChange={(e) => setField("ninea", e.target.value)}
            error={fieldErrors.ninea}
            hint="9 chiffres, suivis éventuellement d'un code régime de 3 caractères."
          />

          <div className="auth-field">
            <span className="auth-label">Forme juridique</span>
            <select
              className={`auth-input ${fieldErrors.formeJuridique ? "has-error" : ""}`}
              value={form.formeJuridique ?? ""}
              onChange={(e) => setField("formeJuridique", e.target.value as FormeJuridique)}
            >
              <option value="" disabled>
                Sélectionnez une forme juridique
              </option>
              {FORMES_JURIDIQUES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            {fieldErrors.formeJuridique && <span className="auth-field-error">{fieldErrors.formeJuridique}</span>}
          </div>

          {rccmEstObligatoire(form.formeJuridique) && (
            <FormField
              label="RCCM"
              placeholder="SN-DKR-2020-B-1234"
              value={form.rccm}
              onChange={(e) => setField("rccm", e.target.value)}
              error={fieldErrors.rccm}
              hint="Obligatoire pour cette forme juridique."
            />
          )}

          <FormField
            label="Secteur d'activité"
            placeholder="Ex : Agroalimentaire"
            value={form.secteurActivite}
            onChange={(e) => setField("secteurActivite", e.target.value)}
            error={fieldErrors.secteurActivite}
          />

          <FormField
            label="Adresse"
            placeholder="Ex : Zone Industrielle, Rue 12, Dakar"
            value={form.adresse}
            onChange={(e) => setField("adresse", e.target.value)}
            error={fieldErrors.adresse}
          />

          <div className="auth-form-grid-2" style={{ marginTop: 18 }}>
            <FormField
              label="Téléphone"
              type="tel"
              placeholder="+221 77 000 00 00"
              value={form.telephone}
              onChange={(e) => setField("telephone", e.target.value)}
              error={fieldErrors.telephone}
              wrapperStyle={{ marginTop: 0 }}
            />
            <FormField
              label="E-mail"
              type="email"
              placeholder="contact@entreprise.sn"
              value={form.email}
              onChange={(e) => setField("email", e.target.value)}
              error={fieldErrors.email}
              wrapperStyle={{ marginTop: 0 }}
            />
          </div>

          <div className="auth-form-grid-2" style={{ marginTop: 18 }}>
            <FormField
              label="Mot de passe"
              type="password"
              placeholder="••••••••"
              value={form.motDePasse}
              onChange={(e) => setField("motDePasse", e.target.value)}
              error={fieldErrors.motDePasse}
              wrapperStyle={{ marginTop: 0 }}
            />
            <FormField
              label="Confirmation"
              type="password"
              placeholder="••••••••"
              value={form.confirmation}
              onChange={(e) => setField("confirmation", e.target.value)}
              error={fieldErrors.confirmation}
              wrapperStyle={{ marginTop: 0 }}
            />
          </div>

          {error && <ErrorBanner message={error} />}

          <button type="submit" className="auth-submit" disabled={submitting}>
            {submitting ? "Création du compte..." : "Créer mon compte"}
          </button>

          <div className="auth-footer-note">
            En créant un compte, vous acceptez que votre entreprise soit soumise à une
            vérification (KYC) avant d'accéder pleinement à la plateforme.
          </div>
        </form>
      </div>

      <div className="auth-switch">
        Déjà un compte ? <Link to="/login">Se connecter</Link>
      </div>
    </AuthLayout>
  );
}

function ConfirmationScreen({
  user,
  accessToken,
  onDone,
}: {
  user: MeResponse;
  accessToken: string;
  onDone: () => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  async function handleFileSelected(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadError(null);
    try {
      await uploadKycDocument(user.entreprise.id, file, accessToken);
      setUploaded(true);
    } catch {
      setUploadError("Le téléversement a échoué. Réessayez ou revenez-y plus tard depuis votre espace.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <AuthLayout>
      <div className="auth-card">
        <div className="auth-confirmation-icon">✓</div>
        <div className="auth-card-title" style={{ textAlign: "center" }}>
          Votre compte a été créé
        </div>
        <div className="auth-card-subtitle" style={{ textAlign: "center" }}>
          {user.entreprise.raison_sociale} est en attente de validation par notre équipe.
        </div>

        {!uploaded ? (
          <>
            <div className="auth-info-banner">
              Prochaine étape : téléversez vos documents KYC (RCCM, NINEA et pièce d'identité du
              représentant légal — regroupés dans un seul fichier PDF si possible) pour accélérer
              la vérification. Vous pouvez aussi le faire plus tard en vous connectant.
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              style={{ display: "none" }}
              onChange={handleFileSelected}
            />

            {uploadError && <ErrorBanner message={uploadError} />}

            <button
              type="button"
              className="auth-submit"
              disabled={uploading}
              onClick={() => fileInputRef.current?.click()}
            >
              {uploading ? "Téléversement..." : "Téléverser mes documents maintenant"}
            </button>
            <button type="button" className="auth-submit-secondary" onClick={onDone}>
              Plus tard
            </button>
          </>
        ) : (
          <>
            <div className="auth-info-banner">
              Documents reçus. Votre dossier est en cours de vérification par notre équipe.
            </div>
            <button type="button" className="auth-submit" onClick={onDone}>
              Aller à la connexion
            </button>
          </>
        )}
      </div>
    </AuthLayout>
  );
}
