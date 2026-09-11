import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { obtenirDashboardAdmin, type DashboardAdminOut } from "../../lib/dashboardApi";
import { obtenirResumeRelations, type RelationResumeOut } from "../../lib/relationsApi";
import { listerEntreprises } from "../../lib/adminApi";
import { listerFactures, type FactureOut } from "../../lib/facturesApi";
import { Sparkline } from "../../components/shell/Sparkline";
import { badgeStatutFacture } from "../../lib/statutFacture";

const AUJOURD_HUI = new Date().toLocaleDateString("fr-FR", {
  weekday: "long",
  year: "numeric",
  month: "long",
  day: "numeric",
});

function fmtMontant(v: string | number): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}

function fmtMd(v: string | number): string {
  const n = Number(v);
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2).replace(".", ",")} Md FCFA`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(".", ",")} M FCFA`;
  return `${fmtMontant(n)} FCFA`;
}

export function AdminDashboard() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [dash, setDash] = useState<DashboardAdminOut | null>(null);
  const [factures, setFactures] = useState<FactureOut[]>([]);
  const [noms, setNoms] = useState<Record<string, string>>({});
  const [relations, setRelations] = useState<RelationResumeOut>({ pilote: 0, convention_signee: 0 });

  useEffect(() => {
    obtenirDashboardAdmin(token).then(setDash).catch(() => {});
    obtenirResumeRelations(token).then(setRelations).catch(() => {});
    listerFactures({}, token).then((f) => setFactures(f.slice(0, 4))).catch(() => {});
    listerEntreprises({}, token)
      .then((entreprises) => {
        const map: Record<string, string> = {};
        entreprises.forEach((e) => (map[e.id] = e.raison_sociale));
        setNoms(map);
      })
      .catch(() => {});
  }, [token]);

  if (!dash) {
    return (
      <>
        <header className="topbar">
          <div>
            <h1>Bonjour, {session!.user.nom ?? "Admin"}</h1>
          </div>
        </header>
        <main>Chargement…</main>
      </>
    );
  }

  const nbPme = dash.entreprises_par_type.PME ?? 0;
  const nbAcheteurs = dash.entreprises_par_type.GRANDE_ENTREPRISE ?? 0;
  const nbPartenaires = dash.entreprises_par_type.PARTENAIRE_FINANCIER ?? 0;

  const volumeTotal =
    Number(dash.repartition_volume.pme ?? 0) +
    Number(dash.repartition_volume.partenaire ?? 0) +
    Number(dash.repartition_volume.plateforme ?? 0);
  const pctPme = volumeTotal > 0 ? (Number(dash.repartition_volume.pme) / volumeTotal) * 100 : 0;
  const pctPartenaire = volumeTotal > 0 ? (Number(dash.repartition_volume.partenaire) / volumeTotal) * 100 : 0;
  const pctPlateforme = 100 - pctPme - pctPartenaire;

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Bonjour, {session!.user.nom ?? "Admin"}</h1>
          <div className="sub">Vue d'ensemble de la plateforme — {AUJOURD_HUI}</div>
        </div>
        <div className="topbar-right">
          <select className="scope">
            <option>Tous les acteurs</option>
            <option>PME</option>
            <option>Acheteurs</option>
            <option>Partenaires</option>
          </select>
          <button className="icon-btn">
            <svg className="ic">
              <use href="#i-bell"></use>
            </svg>
          </button>
          <div className="who">
            <div className="avatar">A</div>
            <div>
              <div className="name">{session!.user.nom ?? "Admin"}</div>
              <div className="role">Administrateur</div>
            </div>
          </div>
        </div>
      </header>

      <main>
        <div className="compliance-banner">
          <svg className="ic">
            <use href="#i-shield"></use>
          </svg>
          <span>
            <b>Conforme à la loi n°09/2026 sur l'affacturage</b> et aux textes OHADA applicables — transactions
            tracées, comptes dédiés, aucune détention de fonds côté plateforme.
          </span>
        </div>

        <div className="kpi-grid">
          <div className="kpi-card">
            <div className="kpi-top">
              <div className="kpi-ic" style={{ background: "var(--green)" }}>
                <svg className="ic">
                  <use href="#i-building"></use>
                </svg>
              </div>
              <div className="kpi-label">PME</div>
            </div>
            <div className="kpi-value">{nbPme}</div>
            <div className="kpi-foot">
              <span className="kpi-delta">+{dash.entreprises_creees_ce_mois.PME ?? 0} ce mois</span>
              <Sparkline values={dash.evolution_entreprises_hebdo.PME ?? []} color="#157A52" />
            </div>
          </div>
          <div className="kpi-card">
            <div className="kpi-top">
              <div className="kpi-ic" style={{ background: "var(--blue)" }}>
                <svg className="ic">
                  <use href="#i-cart"></use>
                </svg>
              </div>
              <div className="kpi-label">ACHETEURS</div>
            </div>
            <div className="kpi-value">{nbAcheteurs}</div>
            <div className="kpi-foot">
              <span className="kpi-delta">+{dash.entreprises_creees_ce_mois.GRANDE_ENTREPRISE ?? 0} ce mois</span>
              <Sparkline values={dash.evolution_entreprises_hebdo.GRANDE_ENTREPRISE ?? []} color="#3B6FA8" />
            </div>
          </div>
          <div className="kpi-card">
            <div className="kpi-top">
              <div className="kpi-ic" style={{ background: "var(--violet)" }}>
                <svg className="ic">
                  <use href="#i-bank"></use>
                </svg>
              </div>
              <div className="kpi-label">PARTENAIRES</div>
            </div>
            <div className="kpi-value">{nbPartenaires}</div>
            <div className="kpi-foot">
              <span className="kpi-delta">+{dash.entreprises_creees_ce_mois.PARTENAIRE_FINANCIER ?? 0} ce mois</span>
              <Sparkline values={dash.evolution_entreprises_hebdo.PARTENAIRE_FINANCIER ?? []} color="#6B5B95" />
            </div>
          </div>
          <div className="kpi-card">
            <div className="kpi-top">
              <div className="kpi-ic" style={{ background: "var(--amber)" }}>
                <svg className="ic">
                  <use href="#i-coin"></use>
                </svg>
              </div>
              <div className="kpi-label">VOLUME FINANCÉ</div>
            </div>
            <div className="kpi-value mono">{fmtMd(dash.montant_total_avance_verse)}</div>
            <div className="kpi-foot">
              <span className="kpi-delta">
                {dash.montant_total_avance_verse_delta_pourcentage != null
                  ? `${Number(dash.montant_total_avance_verse_delta_pourcentage) >= 0 ? "+" : ""}${Number(
                      dash.montant_total_avance_verse_delta_pourcentage,
                    ).toFixed(1)}% ce mois`
                  : "Nouveau ce mois"}
              </span>
              <Sparkline values={dash.evolution_volume_hebdo.map(Number)} color="#C98A3A" />
            </div>
          </div>
        </div>

        <div className="grid-2">
          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Flux d'affacturage</h2>
                <div className="sub">Double validation systématique côté acheteur</div>
              </div>
            </div>
            <div className="flow">
              <div className="flow-step">
                <div className="flow-ic" style={{ background: "var(--green)" }}>
                  <svg className="ic">
                    <use href="#i-building"></use>
                  </svg>
                </div>
                <div className="flow-title">PME</div>
                <div className="flow-sub">Émet la facture</div>
                <div className="flow-count" style={{ background: "var(--green)" }}>
                  {nbPme}
                </div>
              </div>
              <div className="flow-arrow">→</div>
              <div className="flow-step">
                <div className="flow-ic" style={{ background: "var(--blue)" }}>
                  <svg className="ic">
                    <use href="#i-cart"></use>
                  </svg>
                </div>
                <div className="flow-title">Acheteur</div>
                <div className="flow-validation-badge">2 VALIDATEURS REQUIS</div>
                <div className="flow-count" style={{ background: "var(--blue)", marginTop: 4 }}>
                  {nbAcheteurs}
                </div>
              </div>
              <div className="flow-arrow">→</div>
              <div className="flow-step">
                <div className="flow-ic" style={{ background: "var(--violet)" }}>
                  <svg className="ic">
                    <use href="#i-bank"></use>
                  </svg>
                </div>
                <div className="flow-title">Partenaire</div>
                <div className="flow-sub">Finance : 80% puis solde</div>
                <div className="flow-count" style={{ background: "var(--violet)" }}>
                  {nbPartenaires}
                </div>
              </div>
              <div className="flow-arrow">→</div>
              <div className="flow-step">
                <div className="flow-ic" style={{ background: "var(--amber)" }}>
                  <svg className="ic">
                    <use href="#i-shield"></use>
                  </svg>
                </div>
                <div className="flow-title">Admin</div>
                <div className="flow-sub">Supervise la plateforme</div>
                <div className="flow-count" style={{ background: "var(--amber)" }}>
                  {dash.nombre_utilisateurs - nbPme - nbAcheteurs - nbPartenaires >= 0
                    ? dash.nombre_utilisateurs - nbPme - nbAcheteurs - nbPartenaires
                    : "—"}
                </div>
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Onboarding des relations</h2>
                <div className="sub">Pilote vs convention signée</div>
              </div>
            </div>
            {(() => {
              const total = relations.pilote + relations.convention_signee;
              const pctPilote = total > 0 ? (relations.pilote / total) * 100 : 0;
              return (
                <div className="onb-bar">
                  <div className="seg-pilote" style={{ width: `${pctPilote}%` }}></div>
                  <div
                    className="seg-signee"
                    style={{ width: `${100 - pctPilote}%`, background: total > 0 ? undefined : "var(--line)" }}
                  ></div>
                </div>
              );
            })()}
            <div className="onb-legend">
              <span>
                <span className="dot" style={{ background: "var(--amber)" }}></span>Pilote — {relations.pilote}
              </span>
              <span>
                <span className="dot" style={{ background: "var(--green)" }}></span>Signée — {relations.convention_signee}
              </span>
            </div>
          </div>
        </div>

        <div className="grid-2">
          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Demandes récentes</h2>
                <div className="sub">Toutes plateformes confondues</div>
              </div>
              <a className="link-btn" href="/app/admin/factures">
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
                  <th>Garantie</th>
                  <th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {factures.map((f) => {
                  const badge = badgeStatutFacture(f);
                  return (
                    <tr key={f.id}>
                      <td className="mono ref">{f.numero_facture ?? "(brouillon)"}</td>
                      <td>{noms[f.pme_id] ?? "…"}</td>
                      <td>{noms[f.donneur_ordre_id] ?? "…"}</td>
                      <td className="mono">{fmtMontant(f.montant_ttc)}</td>
                      <td>—</td>
                      <td>
                        <span className={`status ${badge.className}`}>{badge.label}</span>
                      </td>
                    </tr>
                  );
                })}
                {factures.length === 0 && (
                  <tr>
                    <td colSpan={6} style={{ color: "var(--muted)", textAlign: "center", padding: "16px 0" }}>
                      Aucune facture pour le moment.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Répartition du volume</h2>
                <div className="sub">{fmtMd(volumeTotal)} — cumul</div>
              </div>
            </div>
            <div className="donut-wrap">
              <div
                className="donut"
                style={{
                  background:
                    volumeTotal > 0
                      ? `conic-gradient(var(--green) 0 ${pctPme}%, var(--blue) ${pctPme}% ${
                          pctPme + pctPartenaire
                        }%, var(--violet) ${pctPme + pctPartenaire}% 100%)`
                      : "var(--line)",
                }}
              >
                <div className="donut-center">
                  <b>{fmtMd(volumeTotal).split(" ")[0]}</b>
                  <span>{fmtMd(volumeTotal).split(" ").slice(1).join(" ")}</span>
                </div>
              </div>
              <div className="legend">
                <div className="legend-item">
                  <span className="legend-dot" style={{ background: "var(--green)" }}></span> PME (avance + solde)
                  <span className="amt">{pctPme.toFixed(0)}%</span>
                </div>
                <div className="legend-item">
                  <span className="legend-dot" style={{ background: "var(--blue)" }}></span> Partenaire (intérêt)
                  <span className="amt">{pctPartenaire.toFixed(0)}%</span>
                </div>
                <div className="legend-item">
                  <span className="legend-dot" style={{ background: "var(--violet)" }}></span> Cedra (commission)
                  <span className="amt">{pctPlateforme.toFixed(0)}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
