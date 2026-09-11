import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth, roleHomePath } from "../../context/AuthContext";
import { DashboardShell } from "../../components/shell/DashboardShell";
import { ACHETEUR_NAV_ITEMS } from "../../lib/acheteurNav";
import { listerFactures } from "../../lib/facturesApi";
import { listerAvoirs } from "../../lib/avoirsApi";
import "../../styles/acheteur-dashboard.css";

export function AcheteurSection() {
  const { session } = useAuth();
  const [badgeValidations, setBadgeValidations] = useState(0);
  const [badgeAvoirs, setBadgeAvoirs] = useState(0);

  const token = session?.accessToken;
  useEffect(() => {
    if (!token) return;
    Promise.all([listerFactures({ statut: "emise" }, token), listerFactures({ statut: "validation_complementaire_requise" }, token)])
      .then(([a, b]) => setBadgeValidations(a.length + b.length))
      .catch(() => {});
    listerAvoirs({ statut: "emis" }, token)
      .then((avoirs) => setBadgeAvoirs(avoirs.length))
      .catch(() => {});
  }, [token]);

  if (!session) return <Navigate to="/login" replace />;
  if (session.user.role !== "validateur_1" && session.user.role !== "validateur_2") {
    return <Navigate to={roleHomePath(session.user.role)} replace />;
  }
  if (session.user.entreprise.statut_kyc !== "valide") {
    return <Navigate to="/app/acheteur/onboarding" replace />;
  }

  const navItems = ACHETEUR_NAV_ITEMS.map((item) => {
    if (item.key === "validations") return { ...item, badge: badgeValidations };
    if (item.key === "avoirs") return { ...item, badge: badgeAvoirs };
    return item;
  });

  return (
    <DashboardShell
      roleClass="role-acheteur"
      brandSub="ACHETEUR"
      navItems={navItems}
      helpBox
    />
  );
}
