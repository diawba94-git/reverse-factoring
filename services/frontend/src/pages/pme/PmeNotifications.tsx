import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { listerNotificationsPme, type NotificationPmeOut } from "../../lib/pmeApi";

type Filtre = "toutes" | "non_lues" | "validations" | "financements" | "litiges";

const ICONES: Record<string, { path: JSX.Element; bg: string }> = {
  validation: {
    bg: "var(--amber)",
    path: (
      <>
        <circle cx="12" cy="12" r="9"></circle>
        <polyline points="12 7 12 12 15 14"></polyline>
      </>
    ),
  },
  financement: {
    bg: "var(--blue)",
    path: (
      <>
        <rect x="2" y="5" width="20" height="14" rx="2"></rect>
        <line x1="2" y1="10" x2="22" y2="10"></line>
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
  acheteur: {
    bg: "var(--green)",
    path: <path d="M6 8a6 6 0 1112 0c0 7 3 9 3 9H3s3-2 3-9"></path>,
  },
  kyc: {
    bg: "var(--muted)",
    path: (
      <>
        <circle cx="12" cy="12" r="9"></circle>
        <line x1="12" y1="16" x2="12" y2="12"></line>
        <line x1="12" y1="8" x2="12.01" y2="8"></line>
      </>
    ),
  },
  invitation: {
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

export function PmeNotifications() {
  const { session } = useAuth();
  const token = session!.accessToken;

  const [notifications, setNotifications] = useState<NotificationPmeOut[] | null>(null);
  const [filtre, setFiltre] = useState<Filtre>("toutes");

  useEffect(() => {
    listerNotificationsPme(token).then(setNotifications).catch(() => setNotifications([]));
  }, [token]);

  const nonLues = (notifications ?? []).filter((n) => !n.lu).length;

  const filtrees = useMemo(() => {
    if (!notifications) return [];
    switch (filtre) {
      case "non_lues":
        return notifications.filter((n) => !n.lu);
      case "validations":
        return notifications.filter((n) => n.type === "validation");
      case "financements":
        return notifications.filter((n) => n.type === "financement");
      case "litiges":
        return notifications.filter((n) => n.type === "litige");
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
          <button className={`notif-chip ${filtre === "validations" ? "active" : ""}`} onClick={() => setFiltre("validations")}>
            Validations
          </button>
          <button className={`notif-chip ${filtre === "financements" ? "active" : ""}`} onClick={() => setFiltre("financements")}>
            Financements
          </button>
          <button className={`notif-chip ${filtre === "litiges" ? "active" : ""}`} onClick={() => setFiltre("litiges")}>
            Litiges
          </button>
        </div>
        <div className="panel" style={{ padding: 0, overflow: "auto" }}>
          {filtrees.map((n, i) => {
            const icone = ICONES[n.type] ?? ICONES.validation;
            return (
              <div className={`notif-list-item ${!n.lu ? "unread" : ""}`} key={i}>
                <div className="notif-ic2" style={{ background: icone.bg }}>
                  <svg viewBox="0 0 24 24">{icone.path}</svg>
                </div>
                <div className="notif-body2">
                  <div className="t">{n.titre}</div>
                  <div className="d">{n.description}</div>
                </div>
                {!n.lu && <span className="unread-dot2"></span>}
                <div className="notif-time2">{tempsEcoule(n.date)}</div>
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
