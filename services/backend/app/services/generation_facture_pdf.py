"""Genere le PDF d'une facture a creation native, a partir d'un template HTML/Jinja2
rendu en PDF par WeasyPrint. Contrairement a une facture importee ou televersee, ce
document est produit par Cedra lui-meme : il n'a donc pas besoin de repasser par le
controle de conformite (app.services.conformite_facture), qui existe pour verifier des
documents dont Cedra ne maitrise pas l'origine."""

from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.models.entreprise import Entreprise
from app.models.facture import Facture
from app.services.logo_pdf import dessiner_wordmark

_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
_env = Environment(loader=FileSystemLoader(_TEMPLATES_DIR))


def _fmt(montant: Decimal) -> str:
    return f"{montant:,.2f}".replace(",", " ").replace(".", ",")


def _generer_pdf_fallback(facture: Facture, pme: Entreprise, donneur_ordre: Entreprise) -> bytes:
    """Repli utilise quand WeasyPrint est indisponible (bibliotheques natives Pango/GObject
    absentes, cas courant d'une machine de developpement Windows sans ces paquets systeme
    installes manuellement — Docker/production les a via le Dockerfile). Moins soigne que
    le rendu HTML/CSS de WeasyPrint, mais reprend les memes donnees reelles : la creation
    de facture ne doit jamais echouer faute de cette seule dependance de mise en forme."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    dessiner_wordmark(pdf, 15, 12, 9)
    pdf.set_y(28)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, text="FACTURE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, text=f"N° {facture.numero_facture or 'Brouillon (non transmise)'}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, text="Émetteur", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, text=pme.raison_sociale, new_x="LMARGIN", new_y="NEXT")
    if pme.adresse:
        pdf.cell(0, 6, text=pme.adresse, new_x="LMARGIN", new_y="NEXT")
    if pme.contact_telephone:
        pdf.cell(0, 6, text=f"Tél : {pme.contact_telephone}", new_x="LMARGIN", new_y="NEXT")
    if pme.contact_email:
        pdf.cell(0, 6, text=f"Mail : {pme.contact_email}", new_x="LMARGIN", new_y="NEXT")
    if pme.ninea:
        pdf.cell(0, 6, text=f"NINEA : {pme.ninea}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, text="Destinataire", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, text=donneur_ordre.raison_sociale, new_x="LMARGIN", new_y="NEXT")
    if donneur_ordre.adresse:
        pdf.cell(0, 6, text=donneur_ordre.adresse, new_x="LMARGIN", new_y="NEXT")
    if donneur_ordre.contact_telephone:
        pdf.cell(0, 6, text=f"Tél : {donneur_ordre.contact_telephone}", new_x="LMARGIN", new_y="NEXT")
    if donneur_ordre.contact_email:
        pdf.cell(0, 6, text=f"Mail : {donneur_ordre.contact_email}", new_x="LMARGIN", new_y="NEXT")
    if donneur_ordre.ninea:
        pdf.cell(0, 6, text=f"NINEA : {donneur_ordre.ninea}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.cell(0, 6, text=f"Date d'émission : {facture.date_emission.strftime('%d/%m/%Y')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, text=f"Date d'échéance : {facture.date_echeance.strftime('%d/%m/%Y')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(90, 7, text="Désignation", border=1)
    pdf.cell(25, 7, text="Qté", border=1, align="R")
    pdf.cell(35, 7, text="Prix unitaire", border=1, align="R")
    pdf.cell(35, 7, text="Total", border=1, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    for ligne in sorted(facture.lignes, key=lambda l: l.ordre):
        pdf.cell(90, 7, text=ligne.designation[:45], border=1)
        pdf.cell(25, 7, text=_fmt(ligne.quantite), border=1, align="R")
        pdf.cell(35, 7, text=_fmt(ligne.prix_unitaire), border=1, align="R")
        pdf.cell(35, 7, text=_fmt(ligne.montant_ligne), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.cell(150, 6, text="Montant HT", align="R")
    pdf.cell(35, 6, text=f"{_fmt(facture.montant_ht)} {facture.devise}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(150, 6, text=f"TVA ({(facture.taux_tva * 100).normalize()}%)", align="R")
    pdf.cell(35, 6, text=f"{_fmt(facture.montant_tva)} {facture.devise}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(150, 8, text="Montant TTC", align="R")
    pdf.cell(35, 8, text=f"{_fmt(facture.montant_ttc)} {facture.devise}", align="R", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


def generer_pdf_facture(facture: Facture, pme: Entreprise, donneur_ordre: Entreprise) -> bytes:
    # Import differe : WeasyPrint necessite des bibliotheques natives (Pango/GObject) absentes
    # d'un environnement de dev sans ces paquets systeme. En le different jusqu'ici (plutot
    # qu'au niveau module), le reste de l'application demarre et se teste normalement meme
    # sans ces libs — seule la generation effective d'un PDF natif en a besoin. Si l'import
    # echoue malgre tout (meme cas), on degrade vers _generer_pdf_fallback plutot que de
    # faire echouer la creation de facture pour une simple limitation de mise en forme.
    try:
        from weasyprint import HTML
    except OSError:
        return _generer_pdf_fallback(facture, pme, donneur_ordre)

    template = _env.get_template("facture.html")

    lignes = [
        {
            "designation": ligne.designation,
            "description": ligne.description,
            "quantite": _fmt(ligne.quantite),
            "prix_unitaire_fmt": _fmt(ligne.prix_unitaire),
            "montant_ligne_fmt": _fmt(ligne.montant_ligne),
        }
        for ligne in sorted(facture.lignes, key=lambda l: l.ordre)
    ]

    html_rendu = template.render(
        facture=facture,
        pme=pme,
        donneur_ordre=donneur_ordre,
        lignes=lignes,
        montant_ht_fmt=_fmt(facture.montant_ht),
        montant_tva_fmt=_fmt(facture.montant_tva),
        montant_ttc_fmt=_fmt(facture.montant_ttc),
        taux_tva_pct=(facture.taux_tva * 100).normalize(),
        numero_affiche=facture.numero_facture or "Brouillon (non transmise)",
    )

    try:
        return HTML(string=html_rendu).write_pdf()
    except OSError:
        return _generer_pdf_fallback(facture, pme, donneur_ordre)
