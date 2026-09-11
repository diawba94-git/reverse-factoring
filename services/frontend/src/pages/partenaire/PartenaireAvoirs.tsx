import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { listerEntreprises } from "../../lib/adminApi";
import { listerFactures, type FactureOut } from "../../lib/facturesApi";
import { listerToutesAvances, type AvanceOut } from "../../lib/pmeApi";
import { listerAvoirs, type AvoirOut } from "../../lib/avoirsApi";

const MOTIF_LABELS: Record<string, string> = {
  retour_partiel: "retour partiel",
  erreur_prix: "erreur de prix",
  remise_commerciale: "remise commerciale",
  autre: "autre motif",
};

function fmt(v: string): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}

export function PartenaireAvoirs() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [avoirs, setAvoirs] = useState<AvoirOut[] | null>(null);
  const [factures, setFactures] = useState<FactureOut[]>([]);
  const [avances, setAvances] = useState<AvanceOut[]>([]);
  const [noms, setNoms] = useState<Record<string, string>>({});

  useEffect(() => {
    listerAvoirs({}, token).then(setAvoirs).catch(() => setAvoirs([]));
    listerFactures({}, token).then(setFactures).catch(() => {});
    listerToutesAvances({}, token).then(setAvances).catch(() => {});
    listerEntreprises({}, token)
      .then((es) => {
        const map: Record<string, string> = {};
        es.forEach((e) => (map[e.id] = e.raison_sociale));
        setNoms(map);
      })
      .catch(() => {});
  }, [token]);

  const facturesParId = useMemo(() => new Map(factures.map((f) => [f.id, f])), [factures]);
  const avancesParFactureId = useMemo(() => new Map(avances.map((a) => [a.facture_id, a])), [avances]);

  // Lecture seule sur les avoirs deja confirmes qui ont reellement impacte un financement
  // (montant_facture_reduit ne touche que la facture, pas encore avancee — hors perimetre
  // de cet ecran, qui ne concerne que "mon portefeuille" de financements).
  const avoirsConfirmes = useMemo(
    () =>
      (avoirs ?? []).filter(
        (a) => a.statut === "confirme_par_acheteur" && (a.effet_applique === "solde_reduit" || a.effet_applique === "creance_creee"),
      ),
    [avoirs],
  );

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Avoirs sur mon portefeuille</h1>
          <div className="sub">
            Corrections commerciales qui impactent vos financements en cours — lecture seule, la confirmation reste
            entre la PME et l'acheteur
          </div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        {avoirsConfirmes.map((a) => {
          const facture = facturesParId.get(a.facture_id);
          const avance = facture ? avancesParFactureId.get(facture.id) : undefined;
          const soldeApres = avance ? Number(avance.montant_solde_du) : 0;
          const deduit = a.montant_deduit_solde ? Number(a.montant_deduit_solde) : Number(a.montant_ttc);
          const soldeAvant = soldeApres + deduit;
          const ecart = Number(a.montant_ttc) - deduit;
          const absorbe = ecart <= 0;
          return (
            <div className="avoir-impact-card" key={a.id} style={absorbe ? { borderLeftColor: "var(--green)" } : undefined}>
              <div className="avoir-impact-head">
                <div>
                  <div className="ref mono">
                    {a.numero_avoir} — confirmé le {new Date(a.created_at).toLocaleDateString("fr-FR")}
                  </div>
                  <div className="title">
                    {facture ? noms[facture.pme_id] ?? "…" : "…"} — facture {facture?.numero_facture ?? "…"} (
                    {facture ? noms[facture.donneur_ordre_id] ?? "…" : "…"})
                  </div>
                </div>
                <div className="avoir-impact-amt">
                  <div className="v" style={absorbe ? { color: "var(--green)" } : undefined}>
                    − {fmt(a.montant_ttc)}
                  </div>
                  <div className="l">FCFA · {MOTIF_LABELS[a.motif] ?? a.motif}</div>
                </div>
              </div>
              <div className="avoir-recalc">
                <div>
                  <span>Solde initialement attendu</span>
                  <b>{fmt(String(soldeAvant))} FCFA</b>
                </div>
                <div>
                  <span>Solde recalculé après avoir</span>
                  <b>{fmt(String(soldeApres))} FCFA</b>
                </div>
                <div>
                  <span>Écart non couvert</span>
                  <b style={ecart > 0 ? { color: "var(--red)" } : undefined}>{fmt(String(Math.max(ecart, 0)))} FCFA</b>
                </div>
                <div>
                  <span>Traitement</span>
                  {ecart > 0 ? (
                    <span className="avoir-tag creance">Créance PME — recouvrement automatique</span>
                  ) : (
                    <span className="avoir-tag applied">Absorbé par le solde restant</span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
        {avoirs && avoirsConfirmes.length === 0 && (
          <div className="empty-state">Aucun avoir n'affecte votre portefeuille pour le moment.</div>
        )}
      </main>
    </>
  );
}
