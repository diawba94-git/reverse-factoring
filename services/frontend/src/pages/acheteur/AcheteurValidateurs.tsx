import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../../context/AuthContext";
import { listerValidateursAvecRelations, type ValidateurAvecRelationsOut } from "../../lib/relationsApi";
import { inviterCollegue } from "../../lib/pmeApi";
import { ApiError } from "../../lib/apiClient";

const ROLE_LABEL: Record<string, string> = { validateur_1: "Validateur 1", validateur_2: "Validateur 2" };

export function AcheteurValidateurs() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [validateurs, setValidateurs] = useState<ValidateurAvecRelationsOut[] | null>(null);
  const [formOuvert, setFormOuvert] = useState(false);
  const [nom, setNom] = useState("");
  const [telephone, setTelephone] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"validateur_1" | "validateur_2">("validateur_2");
  const [erreur, setErreur] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);

  function recharger() {
    listerValidateursAvecRelations(token).then(setValidateurs).catch(() => setValidateurs([]));
  }
  useEffect(recharger, [token]);

  async function handleInviter(e: FormEvent) {
    e.preventDefault();
    setErreur(null);
    if (!nom.trim() || !telephone.trim() || !email.trim()) {
      setErreur("Renseignez le nom, le téléphone et l'email du nouveau validateur.");
      return;
    }
    setEnvoi(true);
    try {
      await inviterCollegue(session!.user.entreprise.id, { nom: nom.trim(), telephone: telephone.trim(), email: email.trim(), role }, token);
      setFormOuvert(false);
      setNom("");
      setTelephone("");
      setEmail("");
      recharger();
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : "Impossible d'envoyer l'invitation.");
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Validateurs de l'entreprise</h1>
          <div className="sub">Chaque validateur est affecté à une ou plusieurs relations fournisseur</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        {validateurs?.map((v) => (
          <div className="validateur-card" key={v.utilisateur_id}>
            <div className="validateur-head">
              <div className="validateur-avatar">{(v.nom ?? "?").charAt(0).toUpperCase()}</div>
              <div>
                <div className="validateur-name">{v.nom ?? "(sans nom)"}</div>
                <div className="validateur-role">{ROLE_LABEL[v.role]}</div>
              </div>
            </div>
            <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 6 }}>Affecté aux relations fournisseur suivantes :</div>
            {v.relations.length === 0 && v.relations_en_attente.length === 0 && (
              <div style={{ fontSize: 11.5, color: "var(--muted)", marginBottom: 8 }}>Aucune relation affectée pour le moment.</div>
            )}
            {v.relations.map((r) => (
              <span className="relation-chip" key={r.relation_id}>
                {r.pme_raison_sociale}
              </span>
            ))}
            {v.relations_en_attente.map((r) => (
              <span className="relation-chip pending" key={r.relation_id}>
                {r.pme_raison_sociale} — en attente d'un second validateur
              </span>
            ))}
            <div>
              <button className="add-relation" disabled title="Affectation manuelle à venir">
                + Affecter à une autre PME
              </button>
            </div>
          </div>
        ))}

        {formOuvert ? (
          <div className="panel" style={{ marginTop: 6 }}>
            <h2 style={{ fontSize: 13.6, fontWeight: 600, margin: "0 0 12px" }}>Inviter un nouveau validateur</h2>
            <form onSubmit={handleInviter}>
              <div className="row-2" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
                <div className="field">
                  <label style={{ display: "block", fontSize: 11.5, fontWeight: 600, marginBottom: 5 }}>Nom</label>
                  <input type="text" value={nom} onChange={(e) => setNom(e.target.value)} style={{ width: "100%" }} />
                </div>
                <div className="field">
                  <label style={{ display: "block", fontSize: 11.5, fontWeight: 600, marginBottom: 5 }}>Rôle</label>
                  <select className="select-filter" value={role} onChange={(e) => setRole(e.target.value as "validateur_1" | "validateur_2")} style={{ width: "100%" }}>
                    <option value="validateur_1">Validateur 1</option>
                    <option value="validateur_2">Validateur 2</option>
                  </select>
                </div>
              </div>
              <div className="row-2" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
                <div className="field">
                  <label style={{ display: "block", fontSize: 11.5, fontWeight: 600, marginBottom: 5 }}>Téléphone</label>
                  <input type="tel" value={telephone} onChange={(e) => setTelephone(e.target.value)} style={{ width: "100%" }} />
                </div>
                <div className="field">
                  <label style={{ display: "block", fontSize: 11.5, fontWeight: 600, marginBottom: 5 }}>Email</label>
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} style={{ width: "100%" }} />
                </div>
              </div>
              {erreur && <div style={{ color: "var(--red)", fontSize: 12, marginBottom: 10 }}>{erreur}</div>}
              <div style={{ display: "flex", gap: 8 }}>
                <button type="button" className="add-relation" onClick={() => setFormOuvert(false)}>
                  Annuler
                </button>
                <button
                  type="submit"
                  disabled={envoi}
                  style={{ background: "var(--green)", color: "#fff", border: "none", borderRadius: 20, padding: "6px 16px", fontSize: 11.5, fontWeight: 600, cursor: "pointer" }}
                >
                  {envoi ? "Envoi…" : "Envoyer l'invitation"}
                </button>
              </div>
            </form>
          </div>
        ) : (
          <button
            className="btn-primary"
            style={{ marginTop: 6, background: "var(--green)", color: "#fff", border: "none", borderRadius: 8, padding: "10px 16px", fontSize: 12.8, fontWeight: 600, cursor: "pointer" }}
            onClick={() => setFormOuvert(true)}
          >
            + Inviter un nouveau validateur
          </button>
        )}
      </main>
    </>
  );
}
