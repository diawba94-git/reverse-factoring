import type { ReactNode } from "react";

/** Enveloppe legere (topbar + main, tokens de la maquette admin) pour les ecrans admin
 * existants qui n'ont pas d'equivalent dans les 6 maquettes de reference — on reutilise
 * leur contenu tel quel, sans le redessiner, juste replace sous le nouveau shell. */
export function LegacyAdminScreen({ title, children }: { title: string; children: ReactNode }) {
  return (
    <>
      <div className="generic-topbar">
        <h1>{title}</h1>
      </div>
      <main>{children}</main>
    </>
  );
}

export function ComingSoonAdminScreen({ title }: { title: string }) {
  return (
    <>
      <div className="generic-topbar">
        <h1>{title}</h1>
      </div>
      <main>
        <div className="empty-state">Cet écran n'est pas encore branché sur des données réelles.</div>
      </main>
    </>
  );
}
