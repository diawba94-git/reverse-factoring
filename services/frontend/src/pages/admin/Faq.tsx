import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../../context/AuthContext";
import { ErrorBanner } from "../../components/auth/ErrorBanner";
import { ApiError } from "../../lib/apiClient";
import {
  creerArticleFaq,
  listerArticlesFaq,
  modifierArticleFaq,
  supprimerArticleFaq,
  type ArticleFaqOut,
} from "../../lib/faqApi";
import { PORTEE_FAQ_LABELS } from "../../lib/roles";

export function Faq() {
  const { session } = useAuth();
  const token = session?.accessToken ?? "";

  const [articles, setArticles] = useState<ArticleFaqOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const [question, setQuestion] = useState("");
  const [reponse, setReponse] = useState("");
  const [portee, setPortee] = useState("toutes");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [publishedMsg, setPublishedMsg] = useState<string | null>(null);

  function recharger() {
    if (!token) return;
    setArticles(null);
    setError(null);
    listerArticlesFaq(token)
      .then(setArticles)
      .catch(() => setError("Impossible de charger les articles."));
  }

  useEffect(recharger, [token]);

  async function handlePublish(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (question.trim().length < 5 || reponse.trim().length < 5) {
      setFormError("Question et réponse doivent contenir au moins 5 caractères.");
      return;
    }
    setSubmitting(true);
    try {
      await creerArticleFaq({ question: question.trim(), reponse: reponse.trim(), portee, publie: true }, token);
      setQuestion("");
      setReponse("");
      setPortee("toutes");
      setPublishedMsg("Article publié.");
      recharger();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Une erreur est survenue. Réessayez.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleTogglePublie(a: ArticleFaqOut) {
    setRowError(null);
    setBusyId(a.id);
    try {
      await modifierArticleFaq(a.id, { publie: !a.publie }, token);
      recharger();
    } catch (err) {
      setRowError(err instanceof ApiError ? err.message : "Impossible de modifier cet article.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(a: ArticleFaqOut) {
    setRowError(null);
    setBusyId(a.id);
    try {
      await supprimerArticleFaq(a.id, token);
      recharger();
    } catch (err) {
      setRowError(err instanceof ApiError ? err.message : "Impossible de supprimer cet article.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 18, alignItems: "start" }}>
      <div className="admin-panel">
        <div className="admin-panel-title">Articles publiés</div>
        <div className="admin-panel-subtitle">Visibles dans l'écran d'aide de chaque interface une fois publiés.</div>

        {rowError && <ErrorBanner message={rowError} />}
        {error && <ErrorBanner message={error} />}
        {!error && articles === null && (
          <div className="admin-loading-state">
            <span className="admin-spinner" />
            Chargement...
          </div>
        )}
        {articles !== null && articles.length === 0 && <div className="admin-empty-state">Aucun article pour l'instant.</div>}

        {articles !== null && articles.length > 0 && (
          <table className="admin-table">
            <thead>
              <tr>
                <th>Question</th>
                <th>Interfaces</th>
                <th>Mise à jour</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {articles.map((a) => (
                <tr key={a.id}>
                  <td>{a.question}</td>
                  <td style={{ fontSize: 12.5 }}>{PORTEE_FAQ_LABELS[a.portee] ?? a.portee}</td>
                  <td style={{ fontSize: 12.5, color: "var(--color-text-muted)" }}>
                    {new Date(a.updated_at).toLocaleDateString("fr-FR")}
                  </td>
                  <td>
                    <div className="admin-table-actions">
                      <button
                        type="button"
                        className="admin-button admin-button--secondary admin-button--small"
                        disabled={busyId === a.id}
                        onClick={() => handleTogglePublie(a)}
                      >
                        {a.publie ? "Dépublier" : "Publier"}
                      </button>
                      <button
                        type="button"
                        className="admin-button admin-button--danger admin-button--small"
                        disabled={busyId === a.id}
                        onClick={() => handleDelete(a)}
                      >
                        Supprimer
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="admin-panel">
        <div className="admin-panel-title">Nouvel article</div>
        <form onSubmit={handlePublish}>
          <div className="admin-field">
            <span className="admin-field-label">Question</span>
            <input
              className="admin-select"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Par exemple : comment corriger un NINEA ?"
            />
          </div>
          <div className="admin-field">
            <span className="admin-field-label">Réponse</span>
            <textarea
              className="admin-select"
              style={{ minHeight: 100, resize: "vertical" }}
              value={reponse}
              onChange={(e) => setReponse(e.target.value)}
            />
          </div>
          <div className="admin-field">
            <span className="admin-field-label">Interfaces concernées</span>
            <select className="admin-select" value={portee} onChange={(e) => setPortee(e.target.value)}>
              {Object.entries(PORTEE_FAQ_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          {formError && <ErrorBanner message={formError} />}

          <button type="submit" className="admin-button admin-button--primary" style={{ width: "100%" }} disabled={submitting}>
            {submitting ? "Publication..." : "Publier"}
          </button>

          {publishedMsg && <div className="admin-success-banner" style={{ marginTop: 12 }}>{publishedMsg}</div>}
        </form>
      </div>
    </div>
  );
}
