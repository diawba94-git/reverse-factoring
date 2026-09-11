import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { usePme } from "../../context/PmeContext";
import { PmeGate } from "./PmeSection";
import {
  obtenirDashboardPme,
  listerAvances,
  listerNotificationsPme,
  type DashboardPmeOut,
  type AvanceOut,
  type NotificationPmeOut,
} from "../../lib/pmeApi";
import { listerFactures, type FactureOut } from "../../lib/facturesApi";
import { listerEntreprises } from "../../lib/adminApi";
import { badgeStatutFacture } from "../../lib/statutFacture";
import { Sparkline } from "../../components/shell/Sparkline";

function fmtMontant(v: string | number): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}

function PmeDashboardContent() {
  const { session } = useAuth();
  const { pmeId, pmeNom } = usePme();
  const token = session!.accessToken;
  const navigate = useNavigate();

  const [dash, setDash] = useState<DashboardPmeOut | null>(null);
  const [factures, setFactures] = useState<FactureOut[]>([]);
  const [avances, setAvances] = useState<AvanceOut[]>([]);
  const [noms, setNoms] = useState<Record<string, string>>({});
  const [notifications, setNotifications] = useState<NotificationPmeOut[]>([]);

  useEffect(() => {
    if (!pmeId) return;
    obtenirDashboardPme(pmeId, token).then(setDash).catch(() => {});
    listerFactures({ pme_id: pmeId }, token).then((f) => setFactures(f.slice(0, 4))).catch(() => {});
    listerAvances(pmeId, token).then(setAvances).catch(() => {});
    listerEntreprises({}, token)
      .then((entreprises) => {
        const map: Record<string, string> = {};
        entreprises.forEach((e) => (map[e.id] = e.raison_sociale));
        setNoms(map);
      })
      .catch(() => {});
    listerNotificationsPme(token).then(setNotifications).catch(() => {});
  }, [pmeId, token]);

  if (!dash) {
    return (
      <>
        <header className="topbar">
          <h1>Bienvenue{session!.user.nom ? `, ${session!.user.nom}` : ""}</h1>
        </header>
        <main>Chargement…</main>
      </>
    );
  }

  const parStatut = dash.factures_par_statut;
  const nbEmises = parStatut.emise ?? 0;
  const nbEnValidation = (parStatut.emise ?? 0) + (parStatut.validation_complementaire_requise ?? 0);
  const nbValidees = parStatut.validee ?? 0;
  const nbAvancees = (parStatut.avance_demandee ?? 0) + (parStatut.avance_versee ?? 0);
  const nbAttenteRemb = parStatut.avance_versee ?? 0;
  const nbSoldees = parStatut.soldee ?? 0;
  const nbEmisesTotal = Object.entries(parStatut)
    .filter(([k]) => k !== "brouillon")
    .reduce((acc, [, v]) => acc + v, 0);

  // Evolution reelle des montants percus par la PME (avance + solde), agregee par mois sur
  // les avances effectivement versees — pas de donnee d'exemple.
  const maintenant = new Date();
  const mois = Array.from({ length: 6 }, (_, i) => {
    const d = new Date(maintenant.getFullYear(), maintenant.getMonth() - (5 - i), 1);
    return { annee: d.getFullYear(), mois: d.getMonth() };
  });
  const evolutionMontants = mois.map(({ annee, mois: m }) =>
    avances
      .filter((a) => a.date_versement_initial && new Date(a.date_versement_initial).getFullYear() === annee && new Date(a.date_versement_initial).getMonth() === m)
      .reduce((acc, a) => acc + Number(a.montant_avance_initial), 0),
  );

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Bienvenue, {session!.user.nom ?? "PME"}</h1>
          <div className="sub">{pmeNom ?? ""} — Voici l'état de vos activités d'affacturage</div>
        </div>
        <div className="topbar-right">
          <button className="icon-btn" onClick={() => navigate("/app/pme/notifications")}>
            <svg className="ic">
              <use href="#i-bell"></use>
            </svg>
            {notifications.filter((n) => !n.lu).length > 0 && (
              <span className="dot">{notifications.filter((n) => !n.lu).length}</span>
            )}
          </button>
          <div className="who">
            <div className="avatar">{(session!.user.nom ?? "P")[0]}</div>
            <div>
              <div className="name">{session!.user.nom ?? "Membre PME"}</div>
              <div className="role">Membre PME</div>
            </div>
          </div>
        </div>
      </header>

      <main>
        <div className="kpi-grid">
          <div className="kpi-card">
            <div className="kpi-top">
              <div className="kpi-ic" style={{ background: "var(--green)" }}>
                <svg className="ic">
                  <use href="#i-file"></use>
                </svg>
              </div>
              <div className="kpi-label">FACTURES ÉMISES</div>
            </div>
            <div className="kpi-value">{nbEmisesTotal}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-top">
              <div className="kpi-ic" style={{ background: "var(--amber)" }}>
                <svg className="ic">
                  <use href="#i-clock"></use>
                </svg>
              </div>
              <div className="kpi-label">EN VALIDATION</div>
            </div>
            <div className="kpi-value">{nbEnValidation}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-top">
              <div className="kpi-ic" style={{ background: "var(--blue)" }}>
                <svg className="ic">
                  <use href="#i-card"></use>
                </svg>
              </div>
              <div className="kpi-label">AVANCÉES (80%)</div>
            </div>
            <div className="kpi-value">{nbAvancees}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-top">
              <div className="kpi-ic" style={{ background: "#1F6B45" }}>
                <svg className="ic">
                  <use href="#i-check-circle"></use>
                </svg>
              </div>
              <div className="kpi-label">MONTANT PERÇU</div>
            </div>
            <div className="kpi-value mono">{fmtMontant(dash.montant_total_avance_percu)}</div>
          </div>
        </div>

        <div className="panel" style={{ marginBottom: 12 }}>
          <div className="panel-head">
            <div>
              <h2>Processus d'affacturage</h2>
              <div className="sub">Suivi de vos demandes en cours</div>
            </div>
          </div>
          <div className="flow">
            <div className="flow-step">
              <div className="flow-ic" style={{ background: "var(--green)" }}>
                <svg className="ic">
                  <use href="#i-file"></use>
                </svg>
              </div>
              <div className="flow-title">Facture créée</div>
              <div className="flow-count">{nbEmises}</div>
              <div className="flow-count-label">facture{nbEmises > 1 ? "s" : ""}</div>
            </div>
            <div className="flow-arrow">→</div>
            <div className="flow-step">
              <div className="flow-ic" style={{ background: "var(--amber)" }}>
                <svg className="ic">
                  <use href="#i-clock"></use>
                </svg>
              </div>
              <div className="flow-title">Validation en cours</div>
              <div className="flow-count">{nbEnValidation}</div>
              <div className="flow-count-label">facture{nbEnValidation > 1 ? "s" : ""}</div>
            </div>
            <div className="flow-arrow">→</div>
            <div className="flow-step">
              <div className="flow-ic" style={{ background: "var(--blue)" }}>
                <svg className="ic">
                  <use href="#i-card"></use>
                </svg>
              </div>
              <div className="flow-title">Avancée (80%)</div>
              <div className="flow-count">{nbValidees + nbAvancees}</div>
              <div className="flow-count-label">facture{nbValidees + nbAvancees > 1 ? "s" : ""}</div>
            </div>
            <div className="flow-arrow">→</div>
            <div className="flow-step">
              <div className="flow-ic" style={{ background: "#8C6D3F" }}>
                <svg className="ic">
                  <use href="#i-hourglass"></use>
                </svg>
              </div>
              <div className="flow-title">Attente remb. acheteur</div>
              <div className="flow-count">{nbAttenteRemb}</div>
              <div className="flow-count-label">facture{nbAttenteRemb > 1 ? "s" : ""}</div>
            </div>
            <div className="flow-arrow">→</div>
            <div className="flow-step">
              <div className="flow-ic" style={{ background: "#1F6B45" }}>
                <svg className="ic">
                  <use href="#i-check-circle"></use>
                </svg>
              </div>
              <div className="flow-title">Soldée (20% − frais)</div>
              <div className="flow-count">{nbSoldees}</div>
              <div className="flow-count-label">facture{nbSoldees > 1 ? "s" : ""}</div>
            </div>
          </div>
        </div>

        <div className="grid-2">
          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Mes demandes récentes</h2>
                <div className="sub">Statut détaillé par facture</div>
              </div>
              <a className="link-btn" href="/app/pme/factures">
                Voir tout
              </a>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Référence</th>
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
                    <td colSpan={5} style={{ color: "var(--muted)", textAlign: "center", padding: "16px 0" }}>
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
                <h2>Notifications</h2>
              </div>
              <button type="button" className="link-btn" onClick={() => navigate("/app/pme/notifications")}>
                Voir tout
              </button>
            </div>
            {notifications.slice(0, 4).map((n, i) => (
              <div className="notif" key={i}>
                <div className="notif-dot"></div>
                <div>
                  <div className="t">{n.titre}</div>
                  <div className="time">{new Date(n.date).toLocaleDateString("fr-FR")}</div>
                </div>
              </div>
            ))}
            {notifications.length === 0 && (
              <div style={{ color: "var(--muted)", fontSize: 12, padding: "8px 0" }}>Aucune notification pour le moment.</div>
            )}
            <div className="chart-box">
              <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 6 }}>Évolution des montants perçus (6 mois)</div>
              <Sparkline values={evolutionMontants} color="#157A52" width={260} height={46} />
            </div>
          </div>
        </div>
      </main>
    </>
  );
}

export function PmeDashboard() {
  return (
    <PmeGate>
      <PmeDashboardContent />
    </PmeGate>
  );
}
