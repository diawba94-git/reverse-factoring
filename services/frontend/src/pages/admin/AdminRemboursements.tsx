import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { rapprocherRemboursement, type RemboursementSuperviseOut } from "../../lib/reconciliationApi";
import { listerToutesAvances, type AvanceOut } from "../../lib/pmeApi";
import { listerFactures, type FactureOut } from "../../lib/facturesApi";
import { obtenirCheque, type ChequeGarantieOut } from "../../lib/chequeApi";
import { ApiError, apiFetchPaginated } from "../../lib/apiClient";
import { Pagination } from "../../components/shell/Pagination";

const STATUTS_FILTRE: { value: string; label: string }[] = [
  { value: "", label: "Tous les statuts" },
  { value: "en_attente", label: "En attente" },
  { value: "rapproche", label: "Rapproché" },
  { value: "ecart_detecte", label: "Écart détecté" },
];

const STATUT_BADGE: Record<string, { label: string; cls: string }> = {
  en_attente: { label: "En attente", cls: "validation" },
  rapproche: { label: "Rapproché", cls: "avancee" },
  ecart_detecte: { label: "Écart détecté", cls: "litige" },
};

function formatMontant(value: string): string {
  return Number(value).toLocaleString("fr-FR");
}

export function AdminRemboursements() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [remboursements, setRemboursements] = useState<RemboursementSuperviseOut[] | null>(null);
  const [avances, setAvances] = useState<AvanceOut[]>([]);
  const [factures, setFactures] = useState<FactureOut[]>([]);
  const [cheques, setCheques] = useState<Record<string, ChequeGarantieOut | null>>({});
  const [recherche, setRecherche] = useState("");
  const [statutFiltre, setStatutFiltre] = useState("");
  const [moyenFiltre, setMoyenFiltre] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(25);
  const [total, setTotal] = useState(0);

  function recharger() {
    setRemboursements(null);
    const params = new URLSearchParams();
    if (statutFiltre) params.set("statut_rapprochement", statutFiltre);
    params.set("page", String(page));
    params.set("per_page", String(perPage));
    apiFetchPaginated<RemboursementSuperviseOut>(`/admin/remboursements?${params.toString()}`, token)
      .then(({ items, total: t }) => {
        setRemboursements(items);
        setTotal(t);
      })
      .catch(() => setRemboursements([]));
  }

  useEffect(recharger, [statutFiltre, page, perPage, token]);
  useEffect(() => {
    setPage(1);
  }, [statutFiltre]);

  useEffect(() => {
    listerToutesAvances({}, token).then(setAvances).catch(() => {});
    listerFactures({}, token).then(setFactures).catch(() => {});
  }, [token]);

  const avanceParId = useMemo(() => new Map(avances.map((a) => [a.id, a])), [avances]);
  const factureParId = useMemo(() => new Map(factures.map((f) => [f.id, f])), [factures]);

  useEffect(() => {
    if (!remboursements) return;
    remboursements.forEach((r) => {
      const avance = avanceParId.get(r.avance_id);
      const facture = avance ? factureParId.get(avance.facture_id) : undefined;
      if (!facture || facture.id in cheques) return;
      obtenirCheque(facture.id, token).then((c) => setCheques((prev) => ({ ...prev, [facture.id]: c })));
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remboursements, avanceParId, factureParId]);

  async function handleMarquer(r: RemboursementSuperviseOut, statut: "rapproche" | "ecart_detecte") {
    setErreur(null);
    setBusyId(r.id);
    try {
      await rapprocherRemboursement(r.id, statut, token);
      recharger();
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : "Impossible de mettre à jour ce remboursement.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Remboursements</h1>
          <div className="sub">Rapprochement des paiements reçus des donneurs d'ordre</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        <div className="filters-bar">
          <input
            type="text"
            className="search-input"
            placeholder="Rechercher une référence..."
            value={recherche}
            onChange={(e) => setRecherche(e.target.value)}
          />
          <select className="select-filter" value={statutFiltre} onChange={(e) => setStatutFiltre(e.target.value)}>
            {STATUTS_FILTRE.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
          <select className="select-filter" value={moyenFiltre} onChange={(e) => setMoyenFiltre(e.target.value)}>
            <option value="">Tous les moyens</option>
            <option value="virement">Virement / Wave</option>
            <option value="cheque">Chèque</option>
          </select>
        </div>
        {erreur && <div className="lit-detail" style={{ color: "var(--red)" }}>{erreur}</div>}
        <div className="panel" style={{ padding: 0, overflow: "auto" }}>
          <table>
            <thead>
              <tr>
                <th style={{ padding: "12px 14px 10px" }}>Avance</th>
                <th>Donneur d'ordre</th>
                <th>Montant reçu</th>
                <th>Moyen</th>
                <th>Date encaissement réel</th>
                <th>Rapprochement</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {remboursements
                ?.filter((r) => {
                  const avance = avanceParId.get(r.avance_id);
                  const facture = avance ? factureParId.get(avance.facture_id) : undefined;
                  const cheque = facture ? cheques[facture.id] : undefined;
                  if (recherche.trim() && !(facture?.numero_facture ?? "").toLowerCase().includes(recherche.trim().toLowerCase())) {
                    return false;
                  }
                  if (moyenFiltre === "cheque" && !cheque) return false;
                  if (moyenFiltre === "virement" && cheque) return false;
                  return true;
                })
                .map((r) => {
                const avance = avanceParId.get(r.avance_id);
                const facture = avance ? factureParId.get(avance.facture_id) : undefined;
                const cheque = facture ? cheques[facture.id] : undefined;
                const moyen = cheque ? `Chèque n°${cheque.numero_cheque}` : "Virement";
                const badge = STATUT_BADGE[r.statut_rapprochement];
                return (
                  <tr key={r.id}>
                    <td className="mono ref" style={{ padding: "12px 14px" }}>
                      {facture?.numero_facture ?? r.avance_id.slice(0, 8)}
                    </td>
                    <td>{r.source_entreprise}</td>
                    <td className="mono">{formatMontant(r.montant_recu)}</td>
                    <td>{moyen}</td>
                    <td>{new Date(r.date_reception).toLocaleDateString("fr-FR")}</td>
                    <td>
                      <span className={`status ${badge.cls}`}>{badge.label}</span>
                    </td>
                    <td>
                      {r.statut_rapprochement === "en_attente" && (
                        <div style={{ display: "flex", gap: 6 }}>
                          <button
                            type="button"
                            className="btn-ghost"
                            disabled={busyId === r.id}
                            onClick={() => handleMarquer(r, "rapproche")}
                          >
                            Rapprocher
                          </button>
                          <button
                            type="button"
                            className="btn-danger"
                            disabled={busyId === r.id}
                            onClick={() => handleMarquer(r, "ecart_detecte")}
                          >
                            Signaler un écart
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
              {remboursements && remboursements.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ padding: "20px 14px", textAlign: "center", color: "var(--muted)" }}>
                    Aucun remboursement pour ce filtre.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          <Pagination page={page} perPage={perPage} total={total} onPageChange={setPage} onPerPageChange={(n) => { setPerPage(n); setPage(1); }} />
        </div>
      </main>
    </>
  );
}
