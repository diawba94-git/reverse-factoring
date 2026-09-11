import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { listerFactures, type FactureOut } from "../../lib/facturesApi";
import { listerEntreprises } from "../../lib/adminApi";
import { confirmerAvoir, listerAvoirs, rejeterAvoir, type AvoirOut } from "../../lib/avoirsApi";
import { ErrorBanner } from "../../components/auth/ErrorBanner";
import { ApiError } from "../../lib/apiClient";

const MOTIF_LABELS: Record<string, string> = {
  retour_partiel: "retour partiel",
  erreur_prix: "erreur de prix",
  remise_commerciale: "remise commerciale",
  autre: "autre motif",
};

const STATUT_BADGE: Record<string, { label: string; cls: string }> = {
  confirme_par_acheteur: { label: "Confirmé", cls: "avancee" },
  rejete: { label: "Rejeté", cls: "rejete" },
};

const STATUT_FACTURE_LABELS: Record<string, string> = {
  emise: "émise",
  validee: "validée",
  validation_complementaire_requise: "1/2 validations",
  avance_demandee: "avance demandée",
  avance_versee: "avancée",
  soldee: "soldée",
};

function fmt(v: string): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}

export function AcheteurAvoirs() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [avoirs, setAvoirs] = useState<AvoirOut[] | null>(null);
  const [factures, setFactures] = useState<FactureOut[]>([]);
  const [noms, setNoms] = useState<Record<string, string>>({});
  const [erreur, setErreur] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  function recharger() {
    listerAvoirs({}, token).then(setAvoirs).catch(() => setAvoirs([]));
  }

  useEffect(() => {
    listerFactures({}, token).then(setFactures).catch(() => {});
    listerEntreprises({}, token)
      .then((es) => {
        const map: Record<string, string> = {};
        es.forEach((e) => (map[e.id] = e.raison_sociale));
        setNoms(map);
      })
      .catch(() => {});
    recharger();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function handleConfirmer(avoirId: string) {
    setErreur(null);
    setBusyId(avoirId);
    try {
      await confirmerAvoir(avoirId, token);
      recharger();
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : "Impossible de confirmer cet avoir.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleRejeter(avoirId: string) {
    setErreur(null);
    setBusyId(avoirId);
    try {
      await rejeterAvoir(avoirId, token);
      recharger();
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : "Impossible de rejeter cet avoir.");
    } finally {
      setBusyId(null);
    }
  }

  const enAttente = avoirs?.filter((a) => a.statut === "emis") ?? [];
  const historique = avoirs?.filter((a) => a.statut !== "emis") ?? [];

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Avoirs à confirmer</h1>
          <div className="sub">Corrections commerciales proposées par vos fournisseurs</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        {erreur && <ErrorBanner message={erreur} />}
        {enAttente.map((a) => {
          const facture = factures.find((f) => f.id === a.facture_id);
          return (
            <div className="avoir-card" key={a.id}>
              <div className="avoir-head">
                <div>
                  <div className="ref mono">{a.numero_avoir}</div>
                  <div className="title">
                    {facture ? noms[facture.pme_id] ?? "…" : "…"} — facture {facture?.numero_facture ?? "…"}
                  </div>
                </div>
                <div className="avoir-amount">
                  <div className="v">− {fmt(a.montant_ttc)}</div>
                  <div className="l">FCFA · {MOTIF_LABELS[a.motif] ?? a.motif}</div>
                </div>
              </div>
              <div className="avoir-detail">
                {facture
                  ? `Facture actuellement ${STATUT_FACTURE_LABELS[facture.statut] ?? facture.statut} — la correction s'appliquera avant tout financement.`
                  : "Détail de la facture indisponible."}
              </div>
              <div className="avoir-actions">
                <button type="button" className="btn-ghost2" disabled={busyId === a.id} onClick={() => handleRejeter(a.id)}>
                  Rejeter
                </button>
                <button type="button" className="btn-confirm" disabled={busyId === a.id} onClick={() => handleConfirmer(a.id)}>
                  Confirmer l'avoir
                </button>
              </div>
            </div>
          );
        })}

        <div className="panel" style={{ padding: 0, overflow: "auto", marginTop: 6 }}>
          <table>
            <thead>
              <tr>
                <th style={{ padding: "12px 14px 10px" }}>N° avoir</th>
                <th>Fournisseur</th>
                <th>Facture</th>
                <th>Montant</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {historique.map((a) => {
                const facture = factures.find((f) => f.id === a.facture_id);
                const badge = STATUT_BADGE[a.statut] ?? { label: a.statut, cls: "emis" };
                return (
                  <tr key={a.id}>
                    <td className="mono" style={{ padding: "12px 14px" }}>
                      {a.numero_avoir}
                    </td>
                    <td>{facture ? noms[facture.pme_id] ?? "…" : "…"}</td>
                    <td className="mono">{facture?.numero_facture ?? "…"}</td>
                    <td className="mono">{fmt(a.montant_ttc)}</td>
                    <td>
                      <span className={`status ${badge.cls}`}>{badge.label}</span>
                    </td>
                  </tr>
                );
              })}
              {avoirs && enAttente.length === 0 && historique.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ padding: "20px 14px", textAlign: "center", color: "var(--muted)" }}>
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
