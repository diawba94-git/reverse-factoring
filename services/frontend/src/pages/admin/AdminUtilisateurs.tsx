import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import {
  listerEntreprises,
  modifierUtilisateurAdmin,
  type EntrepriseOut,
  type UtilisateurOut,
} from "../../lib/adminApi";
import { apiFetchPaginated } from "../../lib/apiClient";
import { ROLE_LABELS } from "../../lib/roles";
import type { RoleUtilisateur } from "../../lib/authApi";
import { Pagination } from "../../components/shell/Pagination";

const ROLE_FILTRE: { value: RoleUtilisateur | ""; label: string }[] = [
  { value: "", label: "Tous les rôles" },
  { value: "membre_pme", label: "Membre PME" },
  { value: "validateur_1", label: "Validateur 1" },
  { value: "validateur_2", label: "Validateur 2" },
  { value: "agent_financier", label: "Agent financier" },
  { value: "admin", label: "Admin" },
];

const ROLE_TAG_CLASS: Record<RoleUtilisateur, string> = {
  admin: "admin",
  membre_pme: "membre",
  validateur_1: "validateur",
  validateur_2: "validateur",
  agent_financier: "agent",
};

function formatDerniereConnexion(value: string | null): string {
  if (!value) return "Jamais";
  const date = new Date(value);
  const jours = Math.floor((Date.now() - date.getTime()) / (1000 * 60 * 60 * 24));
  const heure = date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  if (jours <= 0) return `Aujourd'hui, ${heure}`;
  if (jours === 1) return `Hier, ${heure}`;
  return `Il y a ${jours} jours`;
}

export function AdminUtilisateurs() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [utilisateurs, setUtilisateurs] = useState<UtilisateurOut[] | null>(null);
  const [entreprises, setEntreprises] = useState<EntrepriseOut[]>([]);
  const [recherche, setRecherche] = useState("");
  const [roleFiltre, setRoleFiltre] = useState<RoleUtilisateur | "">("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(25);
  const [total, setTotal] = useState(0);

  function recharger() {
    const params = new URLSearchParams();
    if (roleFiltre) params.set("role", roleFiltre);
    params.set("page", String(page));
    params.set("per_page", String(perPage));
    apiFetchPaginated<UtilisateurOut>(`/utilisateurs?${params.toString()}`, token)
      .then(({ items, total: t }) => {
        setUtilisateurs(items);
        setTotal(t);
      })
      .catch(() => setUtilisateurs([]));
  }

  useEffect(recharger, [token, roleFiltre, page, perPage]);
  useEffect(() => {
    setPage(1);
  }, [roleFiltre]);
  useEffect(() => {
    listerEntreprises({}, token).then(setEntreprises).catch(() => {});
  }, [token]);

  const entrepriseNom = useMemo(() => {
    const map = new Map(entreprises.map((e) => [e.id, e.raison_sociale]));
    return (id: string) => map.get(id) ?? "—";
  }, [entreprises]);

  const filtres = useMemo(() => {
    if (!utilisateurs) return [];
    return utilisateurs.filter((u) => {
      if (recherche.trim()) {
        const q = recherche.trim().toLowerCase();
        const matchNom = (u.nom ?? "").toLowerCase().includes(q);
        const matchEntreprise = entrepriseNom(u.entreprise_id).toLowerCase().includes(q);
        if (!matchNom && !matchEntreprise) return false;
      }
      return true;
    });
  }, [utilisateurs, recherche, entrepriseNom]);

  async function toggleActif(u: UtilisateurOut) {
    setBusyId(u.id);
    try {
      await modifierUtilisateurAdmin(u.id, { compte_actif: !u.compte_actif }, token);
      recharger();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Utilisateurs &amp; rôles</h1>
          <div className="sub">Tous rôles confondus — {utilisateurs?.length ?? "…"} comptes</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        <div className="filters-bar">
          <input
            type="text"
            className="search-input"
            placeholder="Rechercher un nom, une entreprise..."
            value={recherche}
            onChange={(e) => setRecherche(e.target.value)}
          />
          <select className="select-filter" value={roleFiltre} onChange={(e) => setRoleFiltre(e.target.value as RoleUtilisateur | "")}>
            {ROLE_FILTRE.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>
        <div className="panel" style={{ padding: 0, overflow: "auto" }}>
          <table>
            <thead>
              <tr>
                <th style={{ padding: "12px 14px 10px" }}>Utilisateur</th>
                <th>Entreprise</th>
                <th>Rôle</th>
                <th>Dernière connexion</th>
                <th>Statut</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtres.map((u) => (
                <tr key={u.id}>
                  <td style={{ padding: "12px 14px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
                      <div className="user-row-avatar">{(u.nom ?? "?").charAt(0).toUpperCase()}</div>
                      {u.nom ?? "(sans nom)"}
                    </div>
                  </td>
                  <td>{entrepriseNom(u.entreprise_id)}</td>
                  <td>
                    <span className={`role-tag ${ROLE_TAG_CLASS[u.role]}`}>{ROLE_LABELS[u.role]}</span>
                  </td>
                  <td>{formatDerniereConnexion(u.derniere_connexion)}</td>
                  <td>
                    <span className={`status ${u.compte_actif ? "avancee" : "litige"}`}>
                      {u.compte_actif ? "Actif" : "Désactivé"}
                    </span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className={`toggle-active ${u.compte_actif ? "off" : "on"}`}
                      disabled={busyId === u.id}
                      onClick={() => toggleActif(u)}
                    >
                      {u.compte_actif ? "Désactiver" : "Réactiver"}
                    </button>
                  </td>
                </tr>
              ))}
              {filtres.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ padding: "20px 14px", textAlign: "center", color: "var(--muted)" }}>
                    Aucun utilisateur pour ces filtres.
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
