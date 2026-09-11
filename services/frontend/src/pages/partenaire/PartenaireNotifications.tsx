import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { listerNotificationsPartenaire, type NotificationPartenaireOut } from "../../lib/partenaireApi";

type Filtre = "toutes" | "non_lues" | "opportunites" | "litiges" | "remboursements";

const ICONES: Record<string, { path: JSX.Element; bg: string }> = {
  opportunite: {
    bg: "var(--violet)",
    path: <path d="M6 8a6 6 0 1112 0c0 7 3 9 3 9H3s3-2 3-9"></path>,
  },
  echeance: {
    bg: "var(--amber)",
    path: (
      <>
        <circle cx="12" cy="12" r="9"></circle>
        <polyline points="12 7 12 12 15 14"></polyline>
      </>
    ),
  },
  cheque: {
    bg: "var(--green)",
    path: (
      <>
        <path d="M9 12l2 2 4-4"></path>
        <circle cx="12" cy="12" r="9"></circle>
      </>
    ),
  },
  litige: {
    bg: "var(--red)",
    path: (
      <>
        <path d="M12 2 1 21h22z"></path>
        <line x1="12" y1="9" x2="12" y2="13"></line>
        <line x1="12" y1="17" x2="12.01" y2="17"></line>
      </>
    ),
  },
  remboursement: {
    bg: "var(--green)",
    path: (
      <>
        <path d="M9 12l2 2 4-4"></path>
        <circle cx="12" cy="12" r="9"></circle>
      </>
    ),
  },
  convention: {
    bg: "var(--blue)",
    path: <path d="M3 7h6l2 2h10v10H3z"></path>,
  },
};

function tempsEcoule(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 60) return `Il y a ${minutes} min`;
  const heures = Math.floor(minutes / 60);
  if (heures < 24) return `Il y a ${heures}h`;
  const jours = Math.floor(heures / 24);
  if (jours === 1) return "Hier";
  return `Il y a ${jours}j`;
}

export function PartenaireNotifications() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [notifications, setNotifications] = useState<NotificationPartenaireOut[] | null>(null);
  const [filtre, setFiltre] = useState<Filtre>("toutes");

  useEffect(() => {
    listerNotificationsPartenaire(token).then(setNotifications).catch(() => setNotifications([]));
  }, [token]);

  const nonLues = (notifications ?? []).filter((n) => !n.lu).length;

  const filtrees = useMemo(() => {
    if (!notifications) return [];
    switch (filtre) {
      case "non_lues":
        return notifications.filter((n) => !n.lu);
      case "opportunites":
        return notifications.filter((n) => n.type === "opportunite" || n.type === "echeance" || n.type === "cheque");
      case "litiges":
        return notifications.filter((n) => n.type === "litige");
      case "remboursements":
        return notifications.filter((n) => n.type === "remboursement");
      default:
        return notifications;
    }
  }, [notifications, filtre]);

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Notifications</h1>
          <div className="sub">{nonLues} non lue{nonLues > 1 ? "s" : ""}</div>
        </div>
      </header>
      <main style={{ padding: "20px 24px 30px" }}>
        <div className="notif-filters">
          <button className={`notif-chip ${filtre === "toutes" ? "active" : ""}`} onClick={() => setFiltre("toutes")}>
            Toutes ({notifications?.length ?? 0})
          </button>
          <button className={`notif-chip ${filtre === "non_lues" ? "active" : ""}`} onClick={() => setFiltre("non_lues")}>
            Non lues ({nonLues})
          </button>
          <button className={`notif-chip ${filtre === "opportunites" ? "active" : ""}`} onClick={() => setFiltre("opportunites")}>
            Opportunités
          </button>
          <button className={`notif-chip ${filtre === "litiges" ? "active" : ""}`} onClick={() => setFiltre("litiges")}>
            Litiges
          </button>
          <button className={`notif-chip ${filtre === "remboursements" ? "active" : ""}`} onClick={() => setFiltre("remboursements")}>
            Remboursements
          </button>
        </div>
        <div className="panel" style={{ padding: 0, overflow: "auto" }}>
          {filtrees.map((n, i) => {
            const icone = ICONES[n.type] ?? ICONES.opportunite;
            return (
              <div className={`notif-list-item ${!n.lu ? "unread" : ""}`} key={i}>
                <div className="notif-ic" style={{ background: icone.bg }}>
                  <svg viewBox="0 0 24 24">{icone.path}</svg>
                </div>
                <div className="notif-body">
                  <div className="t">{n.titre}</div>
                  <div className="d">{n.description}</div>
                </div>
                {!n.lu && <span className="unread-dot"></span>}
                <div className="notif-time">{tempsEcoule(n.date)}</div>
              </div>
            );
          })}
          {filtrees.length === 0 && (
            <div style={{ padding: "20px 14px", textAlign: "center", color: "var(--muted)" }}>
              Aucune notification pour ce filtre.
            </div>
          )}
        </div>
      </main>
    </>
  );
}
