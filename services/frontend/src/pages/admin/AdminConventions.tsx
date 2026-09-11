import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { listerRelations, type RelationOut } from "../../lib/relationsApi";

function ProgressSignatures({ n }: { n: number }) {
  return (
    <div className="progress-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className={`p3-dot ${i <= n ? "done" : "pending"}`}>
          {i <= n ? "✓" : i}
        </div>
      ))}
      <span style={{ fontSize: 11, color: "var(--muted)", marginLeft: 6 }}>{n}/3</span>
    </div>
  );
}

export function AdminConventions() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [relations, setRelations] = useState<RelationOut[] | null>(null);

  useEffect(() => {
    listerRelations({}, token).then(setRelations).catch(() => setRelations([]));
  }, [token]);

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Conventions &amp; comptes dédiés</h1>
          <div className="sub">Progression des signatures tripartites (PME · Acheteur · Partenaire)</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        <div className="panel" style={{ padding: 0, overflow: "auto" }}>
          <table>
            <thead>
              <tr>
                <th style={{ padding: "12px 14px 10px" }}>PME</th>
                <th>Acheteur</th>
                <th>Compte dédié</th>
                <th>Signatures</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {relations?.map((r) => (
                <tr key={r.id}>
                  <td style={{ padding: "12px 14px" }}>{r.pme_raison_sociale}</td>
                  <td>{r.donneur_ordre_raison_sociale}</td>
                  <td>
                    {r.compte_dedie_statut === "actif" ? (
                      <span className="status avancee">Actif</span>
                    ) : (
                      <span className="status validation">En cours d'ouverture</span>
                    )}
                  </td>
                  <td>
                    <ProgressSignatures n={r.nombre_signatures} />
                  </td>
                  <td>
                    {r.statut === "convention_signee" ? (
                      <span className="status avancee">Convention signée</span>
                    ) : (
                      <span className="status validation">
                        Pilote ({r.factures_pilote_utilisees}/{r.factures_pilote_max} factures)
                      </span>
                    )}
                  </td>
                </tr>
              ))}
              {relations && relations.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ padding: "20px 14px", textAlign: "center", color: "var(--muted)" }}>
                    Aucune relation PME ↔ acheteur pour le moment.
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
