"""Dessine la marque Cedra (icone double-chevron + wordmark) sur un PDF fpdf2, pour que
les documents generes par la plateforme (factures en repli fpdf2, rapports partenaire)
portent la meme identite visuelle que le reste de l'application. Reprend les memes
coordonnees relatives que le SVG de reference (viewBox 56x56, cf. Logo.tsx cote frontend)
plutot que de re-inventer une icone approximative.

Simplification assumee : fpdf2 ne permet pas de regler le style des extremites de trait
(round line caps) aussi facilement qu'en SVG — les chevrons sont donc dessines avec des
extremites carrees (fpdf2 par defaut), une perte de fidelite negligeable a la petite
echelle d'une icone d'en-tete de document imprime."""

from fpdf import FPDF

VERT = (21, 122, 82)  # #157A52
AMBRE = (201, 138, 58)  # #C98A3A
BLANC = (255, 255, 255)
ENCRE = (22, 36, 29)  # #16241D


def _chevron(pdf: FPDF, echelle: float, x0: float, y0: float, ox: float, oy: float) -> None:
    """Dessine un chevron (fleche vers la droite) dont l'origine du path SVG est (ox, oy)
    dans le repere 56x56 d'origine, mis a l'echelle et translate vers (x0, y0)."""

    def pt(px: float, py: float) -> tuple[float, float]:
        return (x0 + px * echelle, y0 + py * echelle)

    depart = pt(ox, oy)
    pointe = pt(ox + 11, oy)
    haut = pt(ox + 11 - 4.4, oy - 4.4)
    bas = pt(ox + 11 - 4.4, oy + 4.4)
    pdf.line(*depart, *pointe)
    pdf.line(*pointe, *haut)
    pdf.line(*pointe, *bas)


def dessiner_icone(pdf: FPDF, x: float, y: float, taille: float) -> None:
    """Dessine l'icone double-chevron (carre arrondi vert, deux chevrons superposes
    blanc + ambre) dans un carre de cote `taille` (mm) dont le coin haut-gauche est (x, y)."""
    echelle = taille / 56.0

    pdf.set_fill_color(*VERT)
    pdf.rect(
        x + 4 * echelle,
        y + 4 * echelle,
        48 * echelle,
        48 * echelle,
        style="F",
        round_corners=True,
        corner_radius=13 * echelle,
    )

    pdf.set_line_width(3.6 * echelle)
    pdf.set_draw_color(*BLANC)
    _chevron(pdf, echelle, x, y, 18, 28)
    pdf.set_draw_color(*AMBRE)
    _chevron(pdf, echelle, x, y, 27, 28)


def dessiner_wordmark(pdf: FPDF, x: float, y: float, taille_icone: float = 8) -> None:
    """Dessine l'icone suivie du mot 'Cedra' (wordmark principal), a utiliser en en-tete
    des documents/exports (factures, rapports) — jamais l'icone seule dans ce contexte."""
    dessiner_icone(pdf, x, y, taille_icone)
    pdf.set_xy(x + taille_icone + 3, y - 1)
    pdf.set_font("Helvetica", "B", taille_icone * 1.7)
    pdf.set_text_color(*ENCRE)
    pdf.cell(30, taille_icone + 2, text="Cedra")
