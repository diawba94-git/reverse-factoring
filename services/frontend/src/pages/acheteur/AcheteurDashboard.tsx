import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { listerFactures, type FactureOut } from "../../lib/facturesApi";
import { listerEntreprises } from "../../lib/adminApi";
import { valider } from "../../lib/validationApi";

function fmt(v: string | number): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}
function fmtDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("fr-FR");
}

const COULEURS = ["var(--green)", "var(--blue)", "var(--violet)", "#B6C7BC"];

export function AcheteurDashboard() {
  const { session } = useAuth();
  const token = session!.accessToken;
  const monRole = session!.user.role as "validateur_1" | "validateur_2";

  const [factures, setFactures] = useState<FactureOut[] | null>(null);
  const [noms, setNoms] = useState<Record<string, string>>({});
  const [enCours, setEnCours] = useState<string | null>(null);

  function recharger() {
    listerFactures({}, token).then(setFactures).catch(() => setFactures([]));
  }
  useEffect(recharger, [token]);
  useEffect(() => {
    listerEntreprises({}, token)
      .then((es) => {
        const map: Record<string, string> = {};
        es.forEach((e) => (map[e.id] = e.raison_sociale));
        setNoms(map);
      })
      .catch(() => {});
  }, [token]);

  const enAttenteValidation = (factures ?? []).filter((f) => f.statut === "emise" || f.statut === "validation_complementaire_requise");
  const doubleValidationOk = (factures ?? []).filter((f) => !["brouillon", "emise", "validation_complementaire_requise"].includes(f.statut));
  const montantTotal = (factures ?? []).reduce((acc, f) => acc + Number(f.montant_ttc), 0);
  const paiementsAVenir = (factures ?? []).filter((f) => f.statut === "avance_versee");

  const parFournisseur = useMemo(() => {
    const counts: Record<string, number> = {};
    (factures ?? []).forEach((f) => {
      counts[f.pme_id] = (counts[f.pme_id] ?? 0) + 1;
    });
    return Object.entries(counts)
      .map(([pmeId, count]) => ({ pmeId, count, nom: noms[pmeId] ?? "…" }))
      .sort((a, b) => b.count - a.count);
  }, [factures, noms]);
  const totalFournisseurs = parFournisseur.reduce((a, f) => a + f.count, 0);

  async function validerFacture(factureId: string) {
    setEnCours(factureId);
    try {
      await valider(factureId, token);
      recharger();
    } catch {
      // erreur silencieuse : la liste ne bouge pas, l'utilisateur peut reessayer
    } finally {
      setEnCours(null);
    }
  }

  if (!factures) {
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
          <h1>Bienvenue, {session!.user.nom ?? "Validateur"}</h1>
          <div className="sub">{session!.user.entreprise.raison_sociale} — Suivez et validez les factures reçues de vos fournisseurs</div>
        </div>
        <div className="topbar-right">
          <button className="icon-btn">
            <svg className="ic">
              <use href="#i-bell"></use>
            </svg>
          </button>
          <div className="who">
            <div className="avatar">{(session!.user.nom ?? "V")[0]}</div>
            <div>
              <div className="name">{session!.user.nom ?? "Validateur"}</div>
              <div className="role">{monRole === "validateur_1" ? "Validateur 1" : "Validateur 2"}</div>
            </div>
          </div>
        </div>
      </header>

      <main>
        <div className="kpi-grid">
          <div className="kpi-card">
            <div className="kpi-top">
              <div className="kpi-ic" style={{ background: "var(--blue)" }}>
                <svg className="ic">
                  <use href="#i-inbox"></use>
                </svg>
              </div>
              <div className="kpi-label">FACTURES REÇUES</div>
            </div>
            <div className="kpi-value">{factures.length}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-top">
              <div className="kpi-ic" style={{ background: "var(--amber)" }}>
                <svg className="ic">
                  <use href="#i-clock-history"></use>
                </svg>
              </div>
              <div className="kpi-label">EN ATTENTE DE VALIDATION</div>
            </div>
            <div className="kpi-value">{enAttenteValidation.length}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-top">
              <div className="kpi-ic" style={{ background: "var(--green)" }}>
                <svg className="ic">
                  <use href="#i-check-double"></use>
                </svg>
              </div>
              <div className="kpi-label">DOUBLE VALIDATION OK</div>
            </div>
            <div className="kpi-value">{doubleValidationOk.length}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-top">
              <div className="kpi-ic" style={{ background: "#1F6B45" }}>
                <svg className="ic">
                  <use href="#i-wallet"></use>
                </svg>
              </div>
              <div className="kpi-label">MONTANT TOTAL</div>
            </div>
            <div className="kpi-value mono">{fmt(montantTotal)}</div>
          </div>
        </div>

        <div className="grid-2">
          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Validations en attente</h2>
                <div className="sub">Chaque facture requiert 2 validateurs distincts, sans exception</div>
              </div>
              <a className="link-btn" href="/app/acheteur/validations">
                Voir tout
              </a>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Référence</th>
                  <th>Fournisseur</th>
                  <th>Montant</th>
                  <th>Progression</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {enAttenteValidation.map((f) => {
                  const dejaValide = f.premiere_validation?.role_validateur;
                  const monRoleAValide = dejaValide === monRole;
                  const label = dejaValide
                    ? `1/2 — ${f.premiere_validation!.nom ?? "Un validateur"} a validé`
                    : "0/2 — aucune validation";
                  return (
                    <tr key={f.id}>
                      <td className="mono ref">{f.numero_facture}</td>
                      <td>{noms[f.pme_id] ?? "…"}</td>
                      <td className="mono">{fmt(f.montant_ttc)}</td>
                      <td>
                        <div className="val-progress">
                          <div className="val-steps">
                            <div className={`val-dot ${dejaValide ? "done" : "pending"}`}>
                              {dejaValide ? (
                                <svg className="ic">
                                  <use href="#i-check"></use>
                                </svg>
                              ) : (
                                "1"
                              )}
                            </div>
                            <div className="val-dot pending">2</div>
                          </div>
                          <span className="val-label">{label}</span>
                        </div>
                      </td>
                      <td>
                        <button
                          className={`btn-validate ${monRoleAValide ? "disabled" : ""}`}
                          disabled={monRoleAValide || enCours === f.id}
                          onClick={() => validerFacture(f.id)}
                        >
                          {monRoleAValide
                            ? `${monRole === "validateur_1" ? "V1" : "V2"} déjà fait`
                            : `Valider (${monRole === "validateur_1" ? "V1" : "V2"})`}
                        </button>
                      </td>
                    </tr>
                  );
                })}
                {enAttenteValidation.length === 0 && (
                  <tr>
                    <td colSpan={5} style={{ color: "var(--muted)", textAlign: "center", padding: "16px 0" }}>
                      Aucune validation en attente.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Statut par fournisseur</h2>
                <div className="sub">{factures.length} facture{factures.length > 1 ? "s" : ""}</div>
              </div>
            </div>
            {totalFournisseurs > 0 ? (
              <div className="donut-wrap">
                <div
                  className="donut"
                  style={{
                    background: `conic-gradient(${(() => {
                      let acc = 0;
                      return parFournisseur
                        .map((f, i) => {
                          const start = acc;
                          acc += (f.count / totalFournisseurs) * 100;
                          return `${COULEURS[i % COULEURS.length]} ${start}% ${acc}%`;
                        })
                        .join(", ");
                    })()})`,
                  }}
                >
                  <div className="donut-center">
                    <b>{totalFournisseurs}</b>
                    <span>Total</span>
                  </div>
                </div>
                <div className="legend">
                  {parFournisseur.slice(0, 4).map((f, i) => (
                    <div className="legend-item" key={f.pmeId}>
                      <span className="legend-dot" style={{ background: COULEURS[i % COULEURS.length] }}></span> {f.nom}
                      <span className="amt">{f.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{ color: "var(--muted)", fontSize: 12 }}>Aucune facture pour le moment.</div>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <div>
              <h2>Paiements à venir</h2>
              <div className="sub">Échéances des factures que vous avez validées</div>
            </div>
          </div>
          <table>
            <thead>
              <tr>
                <th>Référence</th>
                <th>Fournisseur</th>
                <th>Montant</th>
                <th>Échéance</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {paiementsAVenir.map((f) => {
                const enRetard = new Date(f.date_echeance) < new Date();
                return (
                  <tr key={f.id}>
                    <td className="mono ref">{f.numero_facture}</td>
                    <td>{noms[f.pme_id] ?? "…"}</td>
                    <td className="mono">{fmt(f.montant_ttc)}</td>
                    <td>{fmtDate(f.date_echeance)}</td>
                    <td>
                      <span className={`status ${enRetard ? "retard" : "validee"}`}>
                        {enRetard ? "Échéance dépassée" : "À payer au partenaire"}
                      </span>
                    </td>
                  </tr>
                );
              })}
              {paiementsAVenir.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ color: "var(--muted)", textAlign: "center", padding: "16px 0" }}>
                    Aucun paiement à venir pour le moment.
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
