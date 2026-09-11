import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { obtenirMonEnveloppe, listerAvancesPartenaire, listerNotificationsPartenaire, type EnveloppeOut } from "../../lib/partenaireApi";
import { listerFactures, type FactureOut } from "../../lib/facturesApi";
import { listerEntreprises, type EntrepriseOut } from "../../lib/adminApi";
import { listerRelations, type RelationOut } from "../../lib/relationsApi";
import type { AvanceOut } from "../../lib/pmeApi";

function fmt(v: string | number): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}
function fmtMd(v: string | number): string {
  const n = Number(v);
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2).replace(".", ",")} Mds FCFA`;
  return `${fmt(n)} FCFA`;
}

const COULEURS = ["var(--violet)", "var(--blue)", "var(--amber)", "#B6C7BC"];

export function PartenaireDashboard() {
  const { session } = useAuth();
  const navigate = useNavigate();
  const token = session!.accessToken;

  const [enveloppe, setEnveloppe] = useState<EnveloppeOut | null>(null);
  const [avances, setAvances] = useState<AvanceOut[] | null>(null);
  const [factures, setFactures] = useState<Record<string, FactureOut>>({});
  const [entreprises, setEntreprises] = useState<Record<string, EntrepriseOut>>({});
  const [relations, setRelations] = useState<RelationOut[]>([]);
  const [notificationsNonLues, setNotificationsNonLues] = useState(0);

  useEffect(() => {
    obtenirMonEnveloppe(token).then(setEnveloppe).catch(() => {});
    listerAvancesPartenaire({}, token).then(setAvances).catch(() => setAvances([]));
    listerNotificationsPartenaire(token)
      .then((ns) => setNotificationsNonLues(ns.filter((n) => !n.lu).length))
      .catch(() => {});
    listerEntreprises({}, token)
      .then((es) => {
        const map: Record<string, EntrepriseOut> = {};
        es.forEach((e) => (map[e.id] = e));
        setEntreprises(map);
      })
      .catch(() => {});
    listerRelations({}, token).then(setRelations).catch(() => {});
  }, [token]);

  useEffect(() => {
    if (!avances) return;
    listerFactures({}, token)
      .then((fs) => {
        const map: Record<string, FactureOut> = {};
        fs.forEach((f) => (map[f.id] = f));
        setFactures(map);
      })
      .catch(() => {});
  }, [avances, token]);

  const enAttente = (avances ?? []).filter((a) => a.statut === "en_attente_validation");
  const financees = (avances ?? []).filter((a) => a.statut === "avance_versee" || a.statut === "soldee");
  const montantEnPortefeuille = financees.reduce((acc, a) => acc + Number(a.montant_avance_initial), 0);
  const tauxRendement =
    financees.length > 0
      ? (financees.reduce((acc, a) => acc + Number(a.part_partenaire), 0) /
          financees.reduce((acc, a) => acc + Number(a.montant_avance_initial), 0)) *
        100
      : 0;

  const relationParPaire = useMemo(() => {
    const map: Record<string, RelationOut> = {};
    relations.forEach((r) => (map[`${r.pme_id}:${r.donneur_ordre_id}`] = r));
    return map;
  }, [relations]);

  const parSecteur = useMemo(() => {
    const totaux: Record<string, number> = {};
    financees.forEach((a) => {
      const f = factures[a.facture_id];
      if (!f) return;
      const secteur = entreprises[f.donneur_ordre_id]?.secteur_activite ?? "Autres";
      totaux[secteur] = (totaux[secteur] ?? 0) + Number(a.montant_avance_initial);
    });
    return Object.entries(totaux)
      .map(([secteur, montant]) => ({ secteur, montant }))
      .sort((a, b) => b.montant - a.montant);
  }, [financees, factures, entreprises]);
  const totalSecteurs = parSecteur.reduce((a, s) => a + s.montant, 0);

  if (!avances) {
    return (
      <>
        <header className="topbar">
          <h1>Bienvenue{session!.user.nom ? `, ${session!.user.nom}` : ""}</h1>
        </header>
        <main>Chargement…</main>
      </>
    );
  }

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Bienvenue, {session!.user.nom ?? "Analyste Crédit"}</h1>
          <div className="sub">{session!.user.entreprise.raison_sociale} — Vue d'ensemble de votre portefeuille d'affacturage</div>
        </div>
        <div className="topbar-right">
          <button className="icon-btn" onClick={() => navigate("/app/partenaire/notifications")}>
            <svg className="ic">
              <use href="#i-bell"></use>
            </svg>
            {notificationsNonLues > 0 && <span className="dot">{notificationsNonLues}</span>}
          </button>
          <div className="who">
            <div className="avatar">{(session!.user.nom ?? "A")[0]}</div>
            <div>
              <div className="name">{session!.user.nom ?? "Analyste Crédit"}</div>
              <div className="role">Analyste Crédit</div>
            </div>
          </div>
        </div>
      </header>

      <main>
        {enAttente.length > 0 && (
          <div className="sla-banner">
            <svg className="ic">
              <use href="#i-clock"></use>
            </svg>
            <span>
              <b>
                {enAttente.length} demande{enAttente.length > 1 ? "s" : ""} en attente de décision
              </b>{" "}
              — SLA cible : moins de 24h.
            </span>
          </div>
        )}

        <div className="kpi-grid">
          <div className="kpi-card">
            <div className="kpi-top">
              <div className="kpi-ic" style={{ background: "var(--violet)" }}>
                <svg className="ic">
                  <use href="#i-wallet"></use>
                </svg>
              </div>
              <div className="kpi-label">MONTANT DISPONIBLE</div>
            </div>
            <div className="kpi-value mono">{enveloppe ? fmt(enveloppe.montant_disponible) : "—"}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-top">
              <div className="kpi-ic" style={{ background: "var(--blue)" }}>
                <svg className="ic">
                  <use href="#i-trending"></use>
                </svg>
              </div>
              <div className="kpi-label">MONTANT ENGAGÉ</div>
            </div>
            <div className="kpi-value mono">{enveloppe ? fmt(enveloppe.montant_engage) : "—"}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-top">
              <div className="kpi-ic" style={{ background: "var(--green)" }}>
                <svg className="ic">
                  <use href="#i-folder"></use>
                </svg>
              </div>
              <div className="kpi-label">EN PORTEFEUILLE</div>
            </div>
            <div className="kpi-value mono">{fmt(montantEnPortefeuille)}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-top">
              <div className="kpi-ic" style={{ background: "var(--amber)" }}>
                <svg className="ic">
                  <use href="#i-percent"></use>
                </svg>
              </div>
              <div className="kpi-label">TAUX DE RENDEMENT</div>
            </div>
            <div className="kpi-value">{tauxRendement.toFixed(2).replace(".", ",")} %</div>
          </div>
        </div>

        <div className="grid-2">
          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Opportunités de financement</h2>
                <div className="sub">Décision sous 24h — garantie et statut d'onboarding affichés</div>
              </div>
              <a className="link-btn" href="/app/partenaire/opportunites">
                Voir tout
              </a>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Référence</th>
                  <th>PME</th>
                  <th>Acheteur</th>
                  <th>Montant</th>
                  <th>Relation</th>
                  <th>Garantie</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {enAttente.map((a) => {
                  const f = factures[a.facture_id];
                  const relation = f ? relationParPaire[`${f.pme_id}:${f.donneur_ordre_id}`] : undefined;
                  return (
                    <tr key={a.id}>
                      <td className="mono ref">{f?.numero_facture ?? "…"}</td>
                      <td>{f ? entreprises[f.pme_id]?.raison_sociale ?? "…" : "…"}</td>
                      <td>{f ? entreprises[f.donneur_ordre_id]?.raison_sociale ?? "…" : "…"}</td>
                      <td className="mono">{f ? fmt(f.montant_ttc) : "…"}</td>
                      <td>
                        {relation ? (
                          <span className={`status ${relation.statut === "pilote" ? "pilote" : "signee"}`}>
                            {relation.statut === "pilote" ? "Pilote" : "Signée"}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td>
                        {a.garantie_detenue_avant_financement ? (
                          <span className="cheque-flag">
                            <svg className="ic">
                              <use href="#i-check-square"></use>
                            </svg>
                            Confirmé
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td>
                        <button className="btn-decide" onClick={() => navigate(`/app/partenaire/decision/${a.id}`)}>
                          Décider
                        </button>
                      </td>
                    </tr>
                  );
                })}
                {enAttente.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ color: "var(--muted)", textAlign: "center", padding: "16px 0" }}>
                      Aucune opportunité en attente pour le moment.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Répartition par secteur</h2>
                <div className="sub">{fmtMd(montantEnPortefeuille)} en portefeuille</div>
              </div>
            </div>
            {totalSecteurs > 0 ? (
              <div className="donut-wrap">
                <div
                  className="donut"
                  style={{
                    background: `conic-gradient(${(() => {
                      let acc = 0;
                      return parSecteur
                        .map((s, i) => {
                          const start = acc;
                          acc += (s.montant / totalSecteurs) * 100;
                          return `${COULEURS[i % COULEURS.length]} ${start}% ${acc}%`;
                        })
                        .join(", ");
                    })()})`,
                  }}
                >
                  <div className="donut-center">
                    <b>{fmtMd(totalSecteurs).split(" ")[0]}</b>
                    <span>{fmtMd(totalSecteurs).split(" ").slice(1).join(" ")}</span>
                  </div>
                </div>
                <div className="legend">
                  {parSecteur.map((s, i) => (
                    <div className="legend-item" key={s.secteur}>
                      <span className="legend-dot" style={{ background: COULEURS[i % COULEURS.length] }}></span> {s.secteur}
                      <span className="amt">{Math.round((s.montant / totalSecteurs) * 100)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{ color: "var(--muted)", fontSize: 12 }}>Aucun financement en portefeuille pour le moment.</div>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <div>
              <h2>Indicateurs clés du portefeuille</h2>
            </div>
          </div>
          <div className="stat-grid">
            <div className="stat-card">
              <div className="l">PME financées</div>
              <div className="v">{new Set(financees.map((a) => factures[a.facture_id]?.pme_id).filter(Boolean)).size}</div>
            </div>
            <div className="stat-card">
              <div className="l">Acheteurs partenaires</div>
              <div className="v">
                {new Set(financees.map((a) => factures[a.facture_id]?.donneur_ordre_id).filter(Boolean)).size}
              </div>
            </div>
            <div className="stat-card">
              <div className="l">Taux d'impayés</div>
              <div className="v">
                {(avances ?? []).length > 0
                  ? `${(((avances ?? []).filter((a) => a.statut === "en_defaut").length / (avances ?? []).length) * 100).toFixed(2)} %`
                  : "—"}
              </div>
            </div>
            <div className="stat-card">
              <div className="l">Avances en attente</div>
              <div className="v">{enAttente.length}</div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
