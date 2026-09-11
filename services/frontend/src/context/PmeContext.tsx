import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useAuth } from "./AuthContext";
import { listerEntreprisesParType, obtenirEntreprise, type EntrepriseLegereOut } from "../lib/pmeApi";
import type { EntrepriseOut } from "../lib/adminApi";

type PmeContextValue = {
  /** null tant qu'un admin n'a pas encore choisi d'entreprise ; jamais null pour un membre_pme. */
  pmeId: string | null;
  pmeNom: string | null;
  /** Profil complet de l'entreprise consultee (id, statut_kyc, type...), une fois chargee. */
  pmeEntreprise: EntrepriseOut | null;
  isAdmin: boolean;
  pmesDisponibles: EntrepriseLegereOut[] | null;
  selectionnerPme: (id: string) => void;
};

const PmeContext = createContext<PmeContextValue | undefined>(undefined);

export function PmeProvider({ children }: { children: ReactNode }) {
  const { session } = useAuth();
  const isAdmin = session?.user.role === "admin";
  const [pmesDisponibles, setPmesDisponibles] = useState<EntrepriseLegereOut[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pmeEntreprise, setPmeEntreprise] = useState<EntrepriseOut | null>(null);

  useEffect(() => {
    if (!isAdmin || !session) return;
    listerEntreprisesParType("PME", session.accessToken)
      .then(setPmesDisponibles)
      .catch(() => setPmesDisponibles([]));
  }, [isAdmin, session]);

  const pmeId = isAdmin ? selectedId : (session?.user.entreprise.id ?? null);
  const pmeNom = isAdmin
    ? (pmesDisponibles?.find((p) => p.id === selectedId)?.raison_sociale ?? null)
    : (session?.user.entreprise.raison_sociale ?? null);

  useEffect(() => {
    if (!pmeId || !session) {
      setPmeEntreprise(null);
      return;
    }
    obtenirEntreprise(pmeId, session.accessToken)
      .then(setPmeEntreprise)
      .catch(() => setPmeEntreprise(null));
  }, [pmeId, session]);

  return (
    <PmeContext.Provider
      value={{ pmeId, pmeNom, pmeEntreprise, isAdmin, pmesDisponibles, selectionnerPme: setSelectedId }}
    >
      {children}
    </PmeContext.Provider>
  );
}

export function usePme() {
  const ctx = useContext(PmeContext);
  if (!ctx) {
    throw new Error("usePme doit etre utilise a l'interieur d'un PmeProvider");
  }
  return ctx;
}
