import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { listerEntreprises } from "../../lib/adminApi";
import { listerFactures, type FactureOut } from "../../lib/facturesApi";
import { listerAvoirs, listerToutesCreances, type AvoirOut, type CreanceOut, type StatutAvoir } from "../../lib/avoirsApi";

const STATUTS_FILTRE: { value: string; label: string }[] = [
  { value: "", label: "Tous les statuts" },
  { value: "emis", label: "Émis" },
  { value: "confirme_par_acheteur", label: "Confirmé" },
  { value: "rejete", label: "Rejeté" },
];

const STATUT_BADGE: Record<string, { label: string; cls: string }> = {
  emis: { label: "Émis — en attente", cls: "validation" },
  confirme_par_acheteur: { label: "Confirmé", cls: "avancee" },
  rejete: { label: "Rejeté", cls: "litige" },
};

function fmt(v: string): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}

export function AdminAvoirs() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [avoirs, setAvoirs] = useState<AvoirOut[] | null>(null);
  const [factures, setFactures] = useState<FactureOut[]>([]);
  const [creances, setCreances] = useState<CreanceOut[]>([]);
  const [noms, setNoms] = useState<Record<string, string>>({});
  const [recherche, setRecherche] = useState("");
  const [statutFiltre, setStatutFiltre] = useState<StatutAvoir | "">("");

  useEffect(() => {
    listerFactures({}, token).then(setFactures).catch(() => {});
    listerToutesCreances(token).then(setCreances).catch(() => {});
    listerEntreprises({}, token)
      .then((es) => {
        const map: Record<string, string> = {};
        es.forEach((e) => (map[e.id] = e.raison_sociale));
        setNoms(map);
      })
      .catch(() => {});
  }, [token]);

  useEffect(() => {
    listerAvoirs({ statut: statutFiltre || undefined }, token)
      .then(setAvoirs)
      .catch(() => setAvoirs([]));
  }, [token, statutFiltre]);

  const facturesParId = useMemo(() => new Map(factures.map((f) => [f.id, f])), [factures]);
  const avoirsParId = useMemo(() => new Map((avoirs ?? []).map((a) => [a.id, a])), [avoirs]);

  const filtres = useMemo(() => {
    if (!avoirs) return [];
    if (!recherche.trim()) return avoirs;
    const q = recherche.trim().toLowerCase();
    return avoirs.filter((a) => {
      const facture = facturesParId.get(a.facture_id);
      const matchNumero = a.numero_avoir.toLowerCase().includes(q);
      const matchPme = facture ? (noms[facture.pme_id] ?? "").toLowerCase().includes(q) : false;
      return matchNumero || matchPme;
    });
  }, [avoirs, recherche, facturesParId, noms]);

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Avoirs &amp; créances</h1>
          <div className="sub">Supervision globale — corrections commerciales et créances en recouvrement</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        <div className="filters-bar">
          <input
            type="text"
            className="search-input"
            placeholder="Rechercher un avoir, une PME..."
            value={recherche}
            onChange={(e) => setRecherche(e.target.value)}
          />
          <select className="select-filter" value={statutFiltre} onChange={(e) => setStatutFiltre(e.target.value as StatutAvoir | "")}>
            {STATUTS_FILTRE.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        {creances.length > 0 && (
          <div className="panel" style={{ marginBottom: 16 }}>
            <h2 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 12px" }}>Créances en cours de recouvrement</h2>
            {creances.map((c) => {
              const avoirSource = avoirsParId.get(c.avoir_id);
              const soldee = c.statut === "soldee";
              const restant = Number(c.montant_du) - Number(c.montant_recouvre);
              return (
                <div className="creance-card" key={c.id} style={soldee ? { borderLeftColor: "var(--green)" } : undefined}>
                  <div>
                    <div className="t">{noms[c.pme_id] ?? "…"}</div>
                    <div className="d">
                      {soldee
                        ? `Créance intégralement recouvrée${avoirSource ? ` sur l'avoir ${avoirSource.numero_avoir}` : ""}`
                        : `Écart non couvert par le solde restant${avoirSource ? ` sur l'avoir ${avoirSource.numero_avoir}` : ""} — sera déduit automatiquement de la prochaine avance`}
                    </div>
                  </div>
                  <div className="amt" style={soldee ? { color: "var(--green)" } : undefined}>
                    {soldee ? "Soldée" : `${fmt(String(restant))} FCFA`}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="panel" style={{ padding: 0, overflow: "auto" }}>
          <table>
            <thead>
              <tr>
                <th style={{ padding: "12px 14px 10px" }}>N° avoir</th>
                <th>PME</th>
                <th>Acheteur</th>
                <th>Facture</th>
                <th>Montant</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {filtres.map((a) => {
                const facture = facturesParId.get(a.facture_id);
                const badge = STATUT_BADGE[a.statut];
                return (
                  <tr key={a.id}>
                    <td className="mono ref" style={{ padding: "12px 14px" }}>
                      {a.numero_avoir}
                    </td>
                    <td>{facture ? noms[facture.pme_id] ?? "…" : "…"}</td>
                    <td>{facture ? noms[facture.donneur_ordre_id] ?? "…" : "…"}</td>
                    <td className="mono">{facture?.numero_facture ?? "…"}</td>
                    <td className="mono">{fmt(a.montant_ttc)}</td>
                    <td>
                      <span className={`status ${badge.cls}`}>{badge.label}</span>
                    </td>
                  </tr>
                );
              })}
              {filtres.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ padding: "20px 14px", textAlign: "center", color: "var(--muted)" }}>
                    Aucun avoir pour ces filtres.
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
