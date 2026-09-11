import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { detecterDoublons, fusionnerDoublons, type DoublonCandidatOut } from "../../lib/doublonsApi";

function statutLabel(c: DoublonCandidatOut["conserver"]): string {
  if (c.statut_fiche === "pre_inscrite") return "Pré-inscrite";
  return c.statut_kyc === "valide" ? "Active — KYC validé" : "Active — KYC en attente";
}

export function AdminDoublons() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [candidats, setCandidats] = useState<DoublonCandidatOut[] | null>(null);
  const [inverses, setInverses] = useState<Record<number, boolean>>({});
  const [enCours, setEnCours] = useState<number | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    detecterDoublons(token).then(setCandidats).catch(() => setCandidats([]));
  }, [token]);

  function dismiss(index: number) {
    setCandidats((prev) => (prev ? prev.filter((_, i) => i !== index) : prev));
  }

  async function fusionner(index: number) {
    if (!candidats) return;
    const c = candidats[index];
    const swap = inverses[index];
    const conserverId = swap ? c.fusionner.id : c.conserver.id;
    const fusionnerId = swap ? c.conserver.id : c.fusionner.id;
    setEnCours(index);
    setErreur(null);
    try {
      await fusionnerDoublons(conserverId, fusionnerId, token);
      dismiss(index);
    } catch (e) {
      setErreur(e instanceof Error ? e.message : "Échec de la fusion.");
    } finally {
      setEnCours(null);
    }
  }

  return (
    <>
      <header className="topbar">
        <h1>Fusion des fiches en doublon</h1>
        <div className="sub">
          {candidats
            ? `${candidats.length} correspondance${candidats.length > 1 ? "s" : ""} probable${candidats.length > 1 ? "s" : ""} détectée${candidats.length > 1 ? "s" : ""} — vérifiez avant de fusionner, action irréversible`
            : "Analyse en cours…"}
        </div>
      </header>

      <main>
        {erreur && (
          <div className="dup-card" style={{ borderColor: "var(--red)" }}>
            {erreur}
          </div>
        )}

        {candidats && candidats.length === 0 && (
          <div className="empty-state">Aucun doublon probable détecté pour le moment.</div>
        )}

        {candidats?.map((c, index) => {
          const swap = inverses[index] ?? false;
          const conserver = swap ? c.fusionner : c.conserver;
          const fusionner_ = swap ? c.conserver : c.fusionner;
          return (
            <div className="dup-card" key={`${c.conserver.id}-${c.fusionner.id}`}>
              <div className="dup-head">
                <div style={{ fontWeight: 600, fontSize: 13 }}>Correspondance probable</div>
                <div className="match">{Math.round(c.score_similarite * 100)}% de similarité — {c.critere}</div>
              </div>
              <div className="dup-compare">
                <div className="dup-entity keep">
                  <div className="tag">CONSERVER</div>
                  <div className="name">{conserver.raison_sociale}</div>
                  <div className="row">
                    <span>Statut</span>
                    <span>{statutLabel(conserver)}</span>
                  </div>
                  <div className="row">
                    <span>Créée par</span>
                    <span>{conserver.cree_par ?? "—"}</span>
                  </div>
                  <div className="row">
                    <span>Factures liées</span>
                    <span className="mono">{conserver.nombre_factures}</span>
                  </div>
                  <div className="row">
                    <span>Téléphone</span>
                    <span className="mono">{conserver.contact_telephone}</span>
                  </div>
                </div>
                <div className="vs-arrow">→</div>
                <div className="dup-entity">
                  <div className="tag">FUSIONNER ET DÉSACTIVER</div>
                  <div className="name">{fusionner_.raison_sociale}</div>
                  <div className="row">
                    <span>Statut</span>
                    <span>{statutLabel(fusionner_)}</span>
                  </div>
                  <div className="row">
                    <span>Créée par</span>
                    <span>{fusionner_.cree_par ?? "—"}</span>
                  </div>
                  <div className="row">
                    <span>Factures liées</span>
                    <span className="mono">{fusionner_.nombre_factures}</span>
                  </div>
                  <div className="row">
                    <span>Téléphone</span>
                    <span className="mono">{fusionner_.contact_telephone}</span>
                  </div>
                </div>
              </div>
              <div className="select-keep">
                Sens inversé ?{" "}
                <button onClick={() => setInverses((prev) => ({ ...prev, [index]: !swap }))}>
                  Conserver « {fusionner_.raison_sociale} » à la place
                </button>
              </div>
              <div className="dup-actions">
                <button className="btn-ghost" onClick={() => dismiss(index)}>
                  Ce n'est pas un doublon
                </button>
                <button className="btn-merge" disabled={enCours === index} onClick={() => fusionner(index)}>
                  {enCours === index
                    ? "Fusion…"
                    : `Fusionner (${fusionner_.nombre_factures} facture${fusionner_.nombre_factures > 1 ? "s" : ""} réassignée${fusionner_.nombre_factures > 1 ? "s" : ""})`}
                </button>
              </div>
            </div>
          );
        })}
      </main>
    </>
  );
}
