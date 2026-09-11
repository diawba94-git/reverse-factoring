import { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { obtenirPortefeuille, type DonneurOrdrePortefeuilleOut } from "../../lib/partenaireApi";

function fmt(v: string): string {
  return Math.round(Number(v)).toLocaleString("fr-FR").replace(/,/g, " ");
}

export function PartenairePortefeuille() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [lignes, setLignes] = useState<DonneurOrdrePortefeuilleOut[] | null>(null);

  useEffect(() => {
    obtenirPortefeuille(token).then(setLignes).catch(() => setLignes([]));
  }, [token]);

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Portefeuille</h1>
          <div className="sub">Exposition par donneur d'ordre et limites de crédit</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        <div className="panel" style={{ padding: 0, overflow: "auto" }}>
          <table>
            <thead>
              <tr>
                <th style={{ padding: "12px 14px 10px" }}>Donneur d'ordre</th>
                <th>Encours</th>
                <th>Limite de crédit</th>
                <th>Utilisation</th>
                <th>Retards</th>
              </tr>
            </thead>
            <tbody>
              {lignes?.map((l) => {
                const plafond = l.limite_plafond ? Number(l.limite_plafond) : null;
                const utilise = l.limite_utilisee ? Number(l.limite_utilisee) : null;
                const pct = plafond && utilise !== null ? Math.min(100, Math.round((utilise / plafond) * 100)) : null;
                return (
                  <tr key={l.donneur_ordre_id}>
                    <td style={{ padding: "12px 14px" }}>{l.raison_sociale}</td>
                    <td className="mono">{fmt(l.encours)}</td>
                    <td className="mono">{l.limite_plafond ? fmt(l.limite_plafond) : "—"}</td>
                    <td>
                      {pct !== null ? (
                        <>
                          <div className="limit-bar">
                            <div className="fill" style={{ width: `${pct}%`, background: pct >= 80 ? "var(--amber)" : undefined }}></div>
                          </div>
                          <span style={{ fontSize: 11, color: "var(--muted)" }}>{pct}%</span>
                        </>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>{l.retards}</td>
                  </tr>
                );
              })}
              {lignes && lignes.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ padding: "20px 14px", textAlign: "center", color: "var(--muted)" }}>
                    Aucun donneur d'ordre dans votre portefeuille pour le moment.
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
