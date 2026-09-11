import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { usePme } from "../../context/PmeContext";
import { listerDonneursOrdre, listerFactures, type DonneurOrdreOut, type FactureOut } from "../../lib/facturesApi";
import { creerAvoir, listerAvoirs, listerCreancesPme, type AvoirOut, type CreanceOut, type MotifAvoir } from "../../lib/avoirsApi";
import { ErrorBanner } from "../../components/auth/ErrorBanner";
import { ApiError } from "../../lib/apiClient";

const MOTIF_LABELS: Record<MotifAvoir, string> = {
  retour_partiel: "Retour partiel",
  erreur_prix: "Erreur de prix",
  remise_commerciale: "Remise commerciale",
  autre: "Autre",
};

const STATUT_BADGE: Record<string, { label: string; cls: string }> = {
  emis: { label: "Émis — en attente", cls: "emis" },
  confirme_par_acheteur: { label: "Confirmé", cls: "avancee" },
  rejete: { label: "Rejeté", cls: "rejete" },
};

function fmt(v: string): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}

export function PmeAvoirs() {
  const { session } = useAuth();
  const { pmeId } = usePme();
  const token = session!.accessToken;

  const [factures, setFactures] = useState<FactureOut[]>([]);
  const [donneurs, setDonneurs] = useState<DonneurOrdreOut[]>([]);
  const [avoirs, setAvoirs] = useState<AvoirOut[] | null>(null);
  const [creances, setCreances] = useState<CreanceOut[]>([]);

  const [factureId, setFactureId] = useState("");
  const [motif, setMotif] = useState<MotifAvoir>("remise_commerciale");
  const [montantHt, setMontantHt] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);

  function recharger() {
    if (!pmeId) return;
    listerAvoirs({ pme_id: pmeId }, token).then(setAvoirs).catch(() => setAvoirs([]));
    listerCreancesPme(pmeId, token).then(setCreances).catch(() => {});
  }

  useEffect(() => {
    if (!pmeId) return;
    listerFactures({ pme_id: pmeId }, token).then(setFactures).catch(() => {});
    listerDonneursOrdre(token).then(setDonneurs).catch(() => {});
    recharger();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pmeId, token]);

  const facturesEligibles = useMemo(
    () => factures.filter((f) => !["brouillon", "rejetee", "rejetee_conformite"].includes(f.statut)),
    [factures],
  );

  function nomDonneur(id: string): string {
    return donneurs.find((d) => d.id === id)?.raison_sociale ?? "…";
  }

  async function handleSubmit() {
    setErreur(null);
    if (!factureId) {
      setErreur("Sélectionnez une facture.");
      return;
    }
    const ht = Number(montantHt.replace(/\s/g, "").replace(",", "."));
    if (!ht || ht <= 0) {
      setErreur("Indiquez un montant HT valide.");
      return;
    }
    const tva = Math.round(ht * 0.18 * 100) / 100;
    const ttc = Math.round((ht + tva) * 100) / 100;
    setEnvoi(true);
    try {
      await creerAvoir(
        factureId,
        { montant_ht: ht.toFixed(2), montant_tva: tva.toFixed(2), montant_ttc: ttc.toFixed(2), motif },
        token,
      );
      setFactureId("");
      setMontantHt("");
      recharger();
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : "Impossible de créer cet avoir.");
    } finally {
      setEnvoi(false);
    }
  }

  const creanceActive = creances[0];

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Avoirs &amp; créances</h1>
          <div className="sub">Corrections commerciales sur vos factures déjà émises</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        {creanceActive && (
          <div className="creance-banner">
            <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.8} strokeLinecap="round">
              <path d="M12 2 1 21h22z"></path>
              <line x1="12" y1="9" x2="12" y2="13"></line>
              <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
            <div>
              <div className="t">
                Créance en attente — {fmt(String(Number(creanceActive.montant_du) - Number(creanceActive.montant_recouvre)))} FCFA
              </div>
              <div className="d">
                Un avoir a dépassé le solde restant d'une avance. Ce montant sera automatiquement déduit de votre
                prochaine avance, sur n'importe quelle facture — aucune action de votre part n'est nécessaire.
              </div>
            </div>
          </div>
        )}

        <div className="panel" style={{ marginBottom: 16 }}>
          <h2 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 4px" }}>Créer un avoir</h2>
          <p style={{ fontSize: 12, color: "var(--muted)", margin: "0 0 14px" }}>
            L'acheteur devra confirmer avant que la correction ne soit appliquée.
          </p>
          {erreur && <ErrorBanner message={erreur} />}
          <div className="avoir-form">
            <div>
              <label>Facture concernée</label>
              <select value={factureId} onChange={(e) => setFactureId(e.target.value)}>
                <option value="">Sélectionnez une facture</option>
                {facturesEligibles.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.numero_facture ?? "(brouillon)"} — {nomDonneur(f.donneur_ordre_id)} — {fmt(f.montant_ttc)} FCFA
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label>Motif</label>
              <select value={motif} onChange={(e) => setMotif(e.target.value as MotifAvoir)}>
                {Object.entries(MOTIF_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label>Montant HT de la correction</label>
              <input type="text" placeholder="Ex: 500 000" value={montantHt} onChange={(e) => setMontantHt(e.target.value)} />
            </div>
          </div>
          <button type="button" className="btn-primary" style={{ marginTop: 14 }} disabled={envoi} onClick={handleSubmit}>
            {envoi ? "Envoi..." : "Envoyer à l'acheteur pour confirmation"}
          </button>
        </div>

        <div className="panel" style={{ padding: 0, overflow: "auto" }}>
          <table>
            <thead>
              <tr>
                <th style={{ padding: "12px 14px 10px" }}>N° avoir</th>
                <th>Facture</th>
                <th>Acheteur</th>
                <th>Montant</th>
                <th>Motif</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {avoirs?.map((a) => {
                const facture = factures.find((f) => f.id === a.facture_id);
                const badge = STATUT_BADGE[a.statut];
                return (
                  <tr key={a.id}>
                    <td className="mono" style={{ padding: "12px 14px" }}>
                      {a.numero_avoir}
                    </td>
                    <td className="mono">{facture?.numero_facture ?? "…"}</td>
                    <td>{facture ? nomDonneur(facture.donneur_ordre_id) : "…"}</td>
                    <td className="mono">{fmt(a.montant_ttc)}</td>
                    <td>{MOTIF_LABELS[a.motif]}</td>
                    <td>
                      <span className={`status ${badge.cls}`}>{badge.label}</span>
                    </td>
                  </tr>
                );
              })}
              {avoirs && avoirs.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ padding: "20px 14px", textAlign: "center", color: "var(--muted)" }}>
                    Aucun avoir pour le moment.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </main>
    </>
  );
}
