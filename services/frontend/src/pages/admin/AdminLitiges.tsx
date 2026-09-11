import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { agirSurLitige, listerLitiges, type CauseLitige, type LitigeOut } from "../../lib/litigesApi";

// La maquette utilise deux formulations differentes pour la meme cause : "Cheque rejete"
// dans le filtre de la sidebar, "Cheque sans provision" (plus precis) sur la carte elle-meme.
const CAUSE_LABELS_FILTRE: Record<CauseLitige, string> = {
  cheque_sans_provision: "Chèque rejeté",
  contestation_acheteur: "Contestation acheteur",
  ecart_remboursement: "Écart de remboursement",
  autre: "Autre",
};

const CAUSE_LABELS_CARTE: Record<CauseLitige, string> = {
  cheque_sans_provision: "Chèque sans provision",
  contestation_acheteur: "Contestation acheteur",
  ecart_remboursement: "Écart de remboursement",
  autre: "Autre",
};

function fmtMontant(v: string): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}

function depuis(iso: string): string {
  const jours = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000));
  if (jours === 0) return "aujourd'hui";
  return `${jours} jour${jours > 1 ? "s" : ""}`;
}

export function AdminLitiges() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [litiges, setLitiges] = useState<LitigeOut[] | null>(null);
  const [causeFiltre, setCauseFiltre] = useState<CauseLitige | "tous">("tous");
  const [enCours, setEnCours] = useState<string | null>(null);

  function recharger() {
    listerLitiges({}, token).then((l) => setLitiges(l.filter((d) => d.statut !== "resolu"))).catch(() => setLitiges([]));
  }

  useEffect(recharger, [token]);

  const filtres = useMemo(() => {
    if (!litiges) return [];
    const parCauseCount: Partial<Record<CauseLitige, number>> = {};
    litiges.forEach((l) => (parCauseCount[l.cause] = (parCauseCount[l.cause] ?? 0) + 1));
    return (Object.keys(parCauseCount) as CauseLitige[]).map((cause) => ({ cause, count: parCauseCount[cause]! }));
  }, [litiges]);

  const affiches = litiges?.filter((l) => causeFiltre === "tous" || l.cause === causeFiltre) ?? [];

  async function agir(id: string, action: Parameters<typeof agirSurLitige>[1], note?: string) {
    setEnCours(id);
    try {
      await agirSurLitige(id, action, note, token);
      recharger();
    } finally {
      setEnCours(null);
    }
  }

  return (
    <>
      <header className="topbar">
        <h1>Traitement des litiges</h1>
        <div className="sub">
          {litiges ? `${litiges.length} dossier${litiges.length > 1 ? "s" : ""} ouvert${litiges.length > 1 ? "s" : ""}` : "Chargement…"} — instruction
          manuelle requise pour chacun
        </div>
      </header>

      <main>
        <div className="filters">
          <button className={`chip ${causeFiltre === "tous" ? "active" : ""}`} onClick={() => setCauseFiltre("tous")}>
            Tous ({litiges?.length ?? 0})
          </button>
          {filtres.map((f) => (
            <button
              key={f.cause}
              className={`chip ${causeFiltre === f.cause ? "active" : ""}`}
              onClick={() => setCauseFiltre(f.cause)}
            >
              {CAUSE_LABELS_FILTRE[f.cause]} ({f.count})
            </button>
          ))}
        </div>

        {affiches.length === 0 && litiges && (
          <div className="empty-state">Aucun dossier de litige ouvert pour le moment.</div>
        )}

        {affiches.map((l) => (
          <div className="lit-card" key={l.id}>
            <div className="lit-head">
              <div>
                <div className="ref mono">{l.numero_facture ?? l.facture_id.slice(0, 8)}</div>
                <div className="title">
                  {l.fournisseur} → {l.acheteur}
                </div>
                <div className="lit-cause" style={{ marginTop: 6 }}>
                  {CAUSE_LABELS_CARTE[l.cause]}
                </div>
              </div>
              <div className="lit-amount">
                <div className="v">{fmtMontant(l.montant_en_jeu)}</div>
                <div className="l">FCFA en jeu</div>
              </div>
            </div>
            <div className="lit-detail">{l.description}</div>
            <div className="lit-meta">
              <span>
                Partenaire concerné : <b>{l.partenaire_concerne ?? "—"}</b>
              </span>
              <span>
                Ouvert depuis : <b>{depuis(l.ouvert_le)}</b>
              </span>
            </div>
            <div className="lit-actions">
              {l.cause === "ecart_remboursement" ? (
                <a className="btn-ghost" href="/app/admin/remboursements" style={{ textDecoration: "none", display: "inline-flex", alignItems: "center" }}>
                  Voir le rapprochement
                </a>
              ) : (
                <button
                  className="btn-ghost"
                  disabled={enCours === l.id}
                  onClick={() => agir(l.id, "contacter_parties")}
                >
                  Contacter les parties
                </button>
              )}
              {l.cause === "cheque_sans_provision" && (
                <button
                  className="btn-danger"
                  disabled={enCours === l.id}
                  onClick={() => agir(l.id, "engager_recouvrement")}
                >
                  Engager le recouvrement (protêt)
                </button>
              )}
              {l.cause === "contestation_acheteur" && (
                <button
                  className="btn-primary"
                  disabled={enCours === l.id}
                  onClick={() => agir(l.id, "proposer_resolution")}
                >
                  Proposer une résolution amiable
                </button>
              )}
              {(l.cause === "ecart_remboursement" || l.cause === "autre") && (
                <button
                  className="btn-primary"
                  disabled={enCours === l.id}
                  onClick={() => agir(l.id, "marquer_resolu", "Résolu depuis le dossier de litige.")}
                >
                  Marquer comme résolu
                </button>
              )}
            </div>
          </div>
        ))}
      </main>
    </>
  );
}
