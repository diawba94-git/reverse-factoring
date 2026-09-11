import "../../styles/logo.css";

type LogoProps = {
  /** "icon" (double-chevron seul, carre vert) — sidebars des 4 interfaces, favicon, avatar
   * systeme. "full" (icone + wordmark "Cedra" souligne en ambre) — landing, login,
   * documents/exports (PDF de facture, rapports). */
  variant?: "icon" | "full";
  /** Cote de l'icone en px (le wordmark met le texte a l'echelle en consequence). */
  size?: number;
  className?: string;
};

/** Icone double-chevron : carre arrondi vert, deux chevrons superposes blanc + ambre,
 * legerement decales pour un effet de profondeur/mouvement. Coordonnees reprises telles
 * quelles depuis la maquette (viewBox 56x56) — ne jamais dupliquer ce SVG ailleurs dans le
 * code, toujours passer par ce composant. */
function LogoIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 56 56" className="cedra-logo-icon" aria-hidden="true">
      <rect x="4" y="4" width="48" height="48" rx="13" fill="#157A52" />
      <path
        d="M18 28h11m0 0l-4.4-4.4m4.4 4.4l-4.4 4.4"
        stroke="#fff"
        strokeWidth="3.6"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <path
        d="M27 28h11m0 0l-4.4-4.4m4.4 4.4l-4.4 4.4"
        stroke="#C98A3A"
        strokeWidth="3.6"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}

/** Composant de marque Cedra partage — ne jamais recopier le SVG de l'icone ni le
 * wordmark ailleurs dans le code. Trois marques distinctes existent (voir la charte) :
 * cette icone double-chevron, le wordmark complet, et un monogramme "C" reserve a l'icone
 * d'application mobile (asset statique separe, hors de ce composant, jamais utilise sur
 * le web) — les deux premieres ne doivent jamais cohabiter avec la troisieme dans un
 * meme contexte. */
export function Logo({ variant = "icon", size = 26, className }: LogoProps) {
  if (variant === "icon") {
    return (
      <span className={`cedra-logo cedra-logo-icon-only ${className ?? ""}`}>
        <LogoIcon size={size} />
      </span>
    );
  }

  return (
    <span className={`cedra-logo cedra-logo-full ${className ?? ""}`} style={{ gap: size * 0.35 }}>
      <LogoIcon size={size} />
      <span className="cedra-logo-wordmark" style={{ fontSize: size * 0.85 }}>
        Cedra
      </span>
    </span>
  );
}
