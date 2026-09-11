import { useState, type FormEvent } from "react";
import { useAuth } from "../../context/AuthContext";
import { creerGrille, type TypePartenaire } from "../../lib/grillesApi";
import { ApiError } from "../../lib/apiClient";

type FormState = {
  nom: string;
  type_partenaire: TypePartenaire;
  taux_total_minimum: string;
  taux_total_maximum: string;
  proportion_cedra: string;
  proportion_partenaire: string;
  duree_minimum_jours: string;
  duree_maximum_jours: string;
  taux_avance: string;
  plafond_montant: string;
};

const FORM_INITIAL: FormState = {
  nom: "Standard — 60-90j",
  type_partenaire: "banque",
  taux_total_minimum: "0.023",
  taux_total_maximum: "0.03",
  proportion_cedra: "0.3333",
  proportion_partenaire: "0.6667",
  duree_minimum_jours: "60",
  duree_maximum_jours: "90",
  taux_avance: "0.80",
  plafond_montant: "",
};

const PLAFOND_TAEG: Record<TypePartenaire, number> = { banque: 0.14, imf: 0.24 };

function previewPourDuree(form: FormState, duree: number) {
  const min = Number(form.duree_minimum_jours);
  const max = Number(form.duree_maximum_jours);
  const tauxMin = Number(form.taux_total_minimum);
  const tauxMax = Number(form.taux_total_maximum);
  const progression = max > min ? (duree - min) / (max - min) : 0;
  const tauxTotal = tauxMin + (tauxMax - tauxMin) * progression;
  const taeg = tauxTotal * (365 / duree);
  const plafond = PLAFOND_TAEG[form.type_partenaire];
  return { tauxTotal, taeg, conforme: taeg <= plafond };
}

export function AdminGrilles() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [form, setForm] = useState<FormState>(FORM_INITIAL);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function setField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  const min = Number(form.duree_minimum_jours) || 60;
  const max = Number(form.duree_maximum_jours) || 90;
  const etapes = Array.from(
    new Set([min, Math.round(min + (max - min) / 3), Math.round(min + (2 * (max - min)) / 3), max]),
  ).sort((a, b) => a - b);
  const previews = etapes.map((d) => ({ duree: d, ...previewPourDuree(form, d) }));

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setErreur(null);
    setSucces(null);
    setSubmitting(true);
    try {
      await creerGrille(
        {
          nom: form.nom.trim(),
          type_partenaire: form.type_partenaire,
          taux_total_minimum: form.taux_total_minimum,
          taux_total_maximum: form.taux_total_maximum,
          proportion_cedra: form.proportion_cedra,
          proportion_partenaire: form.proportion_partenaire,
          duree_minimum_jours: Number(form.duree_minimum_jours),
          duree_maximum_jours: Number(form.duree_maximum_jours),
          taux_avance: form.taux_avance,
          plafond_montant: form.plafond_montant.trim() ? form.plafond_montant.trim() : null,
          active: true,
          date_debut_validite: new Date().toISOString().slice(0, 10),
        },
        token,
      );
      setSucces("Grille activée. Elle s'applique désormais à toute nouvelle demande d'avance.");
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : "Impossible d'activer cette grille.");
    } finally {
      setSubmitting(false);
    }
  }

  const toutConforme = previews.every((p) => p.conforme);

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Grilles tarifaires</h1>
          <div className="sub">Barème dégressif — aperçu du calcul avant activation</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        <form onSubmit={handleSubmit} className="facture-master">
          <div className="panel">
            <h2 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 14px" }}>Nouvelle grille</h2>
            <div className="grille-form">
              <div className="grille-field">
                <label>Nom de la grille</label>
                <input type="text" value={form.nom} onChange={(e) => setField("nom", e.target.value)} />
              </div>
              <div className="grille-field">
                <label>Type de partenaire</label>
                <select value={form.type_partenaire} onChange={(e) => setField("type_partenaire", e.target.value as TypePartenaire)}>
                  <option value="imf">IMF</option>
                  <option value="banque">Banque</option>
                </select>
              </div>
              <div className="grille-field">
                <label>Taux total à {form.duree_minimum_jours} jours</label>
                <input
                  type="text"
                  value={form.taux_total_minimum}
                  onChange={(e) => setField("taux_total_minimum", e.target.value)}
                  placeholder="0.023"
                />
              </div>
              <div className="grille-field">
                <label>Taux total à {form.duree_maximum_jours} jours</label>
                <input
                  type="text"
                  value={form.taux_total_maximum}
                  onChange={(e) => setField("taux_total_maximum", e.target.value)}
                  placeholder="0.03"
                />
              </div>
              <div className="grille-field">
                <label>Part Cedra (proportion)</label>
                <input
                  type="text"
                  value={form.proportion_cedra}
                  onChange={(e) => setField("proportion_cedra", e.target.value)}
                  placeholder="0.3333"
                />
              </div>
              <div className="grille-field">
                <label>Part partenaire (proportion)</label>
                <input
                  type="text"
                  value={form.proportion_partenaire}
                  onChange={(e) => setField("proportion_partenaire", e.target.value)}
                  placeholder="0.6667"
                />
              </div>
              <div className="grille-field">
                <label>Durée minimum (jours)</label>
                <input
                  type="text"
                  value={form.duree_minimum_jours}
                  onChange={(e) => setField("duree_minimum_jours", e.target.value)}
                />
              </div>
              <div className="grille-field">
                <label>Durée maximum (jours)</label>
                <input
                  type="text"
                  value={form.duree_maximum_jours}
                  onChange={(e) => setField("duree_maximum_jours", e.target.value)}
                />
              </div>
              <div className="grille-field">
                <label>Taux d'avance</label>
                <input type="text" value={form.taux_avance} onChange={(e) => setField("taux_avance", e.target.value)} placeholder="0.80" />
              </div>
              <div className="grille-field">
                <label>Plafond en FCFA</label>
                <input
                  type="text"
                  value={form.plafond_montant}
                  onChange={(e) => setField("plafond_montant", e.target.value)}
                  placeholder="Aucun"
                  style={{ color: form.plafond_montant ? undefined : "var(--muted)" }}
                />
              </div>
            </div>
            {erreur && <div className="lit-detail" style={{ color: "var(--red)", marginTop: 12 }}>{erreur}</div>}
            {succes && <div className="lit-detail" style={{ color: "var(--green)", marginTop: 12 }}>{succes}</div>}
            <button
              type="submit"
              className="btn-primary"
              disabled={submitting}
              style={{
                width: "100%",
                background: "var(--green)",
                color: "#fff",
                border: "none",
                borderRadius: 8,
                padding: 11,
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
                marginTop: 16,
              }}
            >
              {submitting ? "Activation…" : "Activer cette grille"}
            </button>
          </div>

          <div className="panel">
            <h2 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 10px" }}>Aperçu de conformité TAEG</h2>
            <table className="preview-table">
              <thead>
                <tr>
                  <th>Durée</th>
                  <th>Taux total</th>
                  <th>TAEG annualisé</th>
                  <th>Conforme</th>
                </tr>
              </thead>
              <tbody>
                {previews.map((p) => (
                  <tr key={p.duree}>
                    <td>{p.duree} jours</td>
                    <td>{(p.tauxTotal * 100).toFixed(2)} %</td>
                    <td>{(p.taeg * 100).toFixed(2)} %</td>
                    <td className={p.conforme ? "ok" : undefined} style={p.conforme ? undefined : { color: "var(--red)", fontWeight: 600 }}>
                      {p.conforme ? `✓ ${form.type_partenaire === "imf" ? "IMF" : "Banque"}` : "✗ Non conforme"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div
              className="role-hint"
              style={{
                display: "flex",
                gap: 9,
                background: toutConforme ? "var(--green-soft)" : "#F7DCD8",
                borderRadius: 8,
                padding: "11px 13px",
                fontSize: 11.5,
                color: toutConforme ? "var(--green-dark)" : "#8C2E22",
                marginTop: 14,
              }}
            >
              <span>{toutConforme ? "✓" : "✗"}</span>
              <div>
                {toutConforme
                  ? `Cette grille reste conforme au plafond légal (${form.type_partenaire === "imf" ? "24%" : "14%"}) sur toute la fenêtre ${form.duree_minimum_jours}-${form.duree_maximum_jours} jours — aucun ajustement requis avant activation.`
                  : "Cette grille dépasse le plafond légal sur au moins un point de la fenêtre — ajustez les taux avant d'activer."}
              </div>
            </div>
          </div>
        </form>
      </main>
    </>
  );
}
