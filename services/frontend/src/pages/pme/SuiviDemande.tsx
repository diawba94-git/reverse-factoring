import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { usePme } from "../../context/PmeContext";
import { ErrorBanner } from "../../components/auth/ErrorBanner";
import { listerDonneursOrdre, listerFactures, type DonneurOrdreOut, type FactureOut } from "../../lib/facturesApi";
import { listerAvances, type AvanceOut } from "../../lib/pmeApi";

const STATUT_LABELS: Record<string, string> = {
  en_attente_validation: "en cours",
  avance_versee: "avancée",
  soldee: "soldée",
  en_defaut: "en défaut",
  rejetee: "rejetée",
};

function fmt(v: string): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}
function formatDate(v: string | null): string {
  if (!v) return "—";
  return new Date(v).toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

type Etape = { titre: string; horodatage: string | null; etat: "done" | "current" | "pending" | "echec" };

function construireEtapes(avance: AvanceOut): Etape[] {
  const etapes: Etape[] = [{ titre: "Demande envoyée", horodatage: avance.created_at, etat: "done" }];

  if (avance.statut === "rejetee") {
    etapes.push({ titre: "Demande rejetée par le partenaire financier", horodatage: null, etat: "echec" });
    return etapes;
  }

  etapes.push({
    titre: "Décision du partenaire financier",
    horodatage: avance.statut === "en_attente_validation" ? null : avance.date_versement_initial,
    etat: avance.statut === "en_attente_validation" ? "current" : "done",
  });
  etapes.push({
    titre: "Versement de l'avance (80%)",
    horodatage: avance.date_versement_initial,
    etat: avance.date_versement_initial ? "done" : "pending",
  });
  etapes.push({
    titre: avance.statut === "en_defaut" ? "Remboursement en défaut" : "Remboursement par le donneur d'ordre",
    horodatage: null,
    etat: avance.statut === "en_defaut" ? "echec" : avance.date_versement_solde ? "done" : "pending",
  });
  etapes.push({
    titre: "Versement du solde",
    horodatage: avance.date_versement_solde,
    etat: avance.date_versement_solde ? "done" : "pending",
  });

  return etapes;
}

export function SuiviDemande() {
  const { session } = useAuth();
  const { pmeId } = usePme();
  const token = session?.accessToken ?? "";

  const [avances, setAvances] = useState<AvanceOut[] | null>(null);
  const [factures, setFactures] = useState<FactureOut[] | null>(null);
  const [donneurs, setDonneurs] = useState<DonneurOrdreOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (!pmeId || !token) return;
    setAvances(null);
    setError(null);
    listerAvances(pmeId, token)
      .then(setAvances)
      .catch(() => setError("Impossible de charger les demandes d'avance."));
    listerFactures({ pme_id: pmeId }, token).then(setFactures).catch(() => undefined);
    listerDonneursOrdre(token).then(setDonneurs).catch(() => undefined);
  }, [pmeId, token]);

  function factureDe(avance: AvanceOut): FactureOut | undefined {
    return factures?.find((f) => f.id === avance.facture_id);
  }
  function nomDonneur(id: string | undefined): string {
    return donneurs?.find((d) => d.id === id)?.raison_sociale ?? "…";
  }

  const selected = avances?.find((a) => a.id === selectedId) ?? avances?.[0] ?? null;
  const selectedFacture = selected ? factureDe(selected) : undefined;

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Suivi de mes demandes</h1>
          <div className="sub">Historique et statut de chaque demande d'avance</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        {error && <ErrorBanner message={error} />}
        {avances !== null && avances.length === 0 && <div className="sub">Aucune demande d'avance pour le moment.</div>}
        {avances !== null && avances.length > 0 && (
          <div className="suivi-list">
            <div>
              {avances.map((a) => {
                const facture = factureDe(a);
                const montant = Number(a.montant_avance_initial) + Number(a.montant_solde_du);
                return (
                  <div
                    key={a.id}
                    className={`suivi-item ${selected?.id === a.id ? "selected" : ""}`}
                    onClick={() => setSelectedId(a.id)}
                  >
                    <div className="r1">
                      {facture?.numero_facture ?? a.id.slice(0, 8)} — {nomDonneur(facture?.donneur_ordre_id)}
                    </div>
                    <div className="r2">
                      {fmt(String(montant))} FCFA · {STATUT_LABELS[a.statut] ?? a.statut}
                    </div>
                  </div>
                );
              })}
            </div>

            {selected && (
              <div className="panel">
                <div className="detail-head" style={{ display: "flex", justifyContent: "space-between", marginBottom: 14 }}>
                  <div>
                    <div className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>
                      {selected.id.slice(0, 8)}
                    </div>
                    <div style={{ fontSize: 15, fontWeight: 600, marginTop: 2 }}>
                      {nomDonneur(selectedFacture?.donneur_ordre_id)} — facture {selectedFacture?.numero_facture ?? "—"}
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div className="mono" style={{ fontSize: 19, fontWeight: 700 }}>
                      {fmt(String(Number(selected.montant_avance_initial) + Number(selected.montant_solde_du)))}
                    </div>
                    <div style={{ fontSize: 10, color: "var(--muted)" }}>FCFA · net attendu</div>
                  </div>
                </div>
                <div className="timeline-full">
                  {construireEtapes(selected).map((etape) => (
                    <div className="t-item" key={etape.titre}>
                      <span
                        className={`t-dot2 ${etape.etat === "echec" ? "" : etape.etat}`}
                        style={etape.etat === "echec" ? { background: "var(--red)" } : undefined}
                      />
                      <div>
                        <div style={{ fontSize: 12.6, fontWeight: 600 }}>{etape.titre}</div>
                        <div style={{ fontSize: 10.8, color: "var(--muted)" }}>
                          {etape.horodatage ? formatDate(etape.horodatage) : etape.etat === "current" ? "Réponse attendue sous 24h" : "À venir"}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </>
  );
}
