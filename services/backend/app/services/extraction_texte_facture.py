"""Extraction de texte et de champs structures a partir d'un document facture (PDF ou
image). Regroupe la logique partagee entre le controle de conformite
(app.services.conformite_facture, qui compare les champs extraits au NINEA declare de
l'emetteur) et le pre-remplissage assiste du formulaire de creation de facture
(app.services.extraction_import_facture, qui n'exige aucune correspondance et sert
uniquement de brouillon a relire).

Pipeline : pour un PDF, le texte natif est prefere (fiable) ; si le document est un scan
sans couche de texte, on bascule sur l'OCR (pytesseract) page par page. Pour une image,
l'OCR est la seule option. Le binaire Tesseract n'est pas toujours installe (absent par
defaut sur une machine de developpement Windows) : OcrIndisponibleError est levee dans ce
cas precis pour que l'appelant degrade proprement plutot que de planter avec une 500.
"""

import io
import re
from decimal import Decimal, InvalidOperation

import pdfplumber

SEUIL_TEXTE_NATIF = 30

NINEA_PATTERN = re.compile(r"NINEA\s*[:n°#\-]{0,3}\s*(\d{7,9}[A-Z]{0,2})", re.IGNORECASE)
MONTANT_HT_PATTERN = re.compile(r"(?:MONTANT\s+)?(?:TOTAL\s+)?HT\b\s*[:\-]?\s*([\d][\d\s.,]*\d|\d)", re.IGNORECASE)
MONTANT_TVA_PATTERN = re.compile(
    r"(?:MONTANT\s+)?TVA\s*(?:\(?\s*\d{1,2}(?:[.,]\d+)?\s*%\s*\)?)?\s*[:\-]?\s*([\d][\d\s.,]*\d|\d)", re.IGNORECASE
)
MONTANT_TTC_PATTERN = re.compile(
    r"(?:(?:MONTANT|TOTAL)\s+TTC|NET\s+A\s+PAYER|TOTAL\s+GENERAL)\s*[:\-]?\s*([\d][\d\s.,]*\d|\d)", re.IGNORECASE
)
TAUX_TVA_PATTERN = re.compile(r"TVA\D{0,10}?(\d{1,2}(?:[.,]\d+)?)\s*%", re.IGNORECASE)
NUMERO_FACTURE_PATTERN = re.compile(r"(?:FACTURE\s*N[°o]?|N[°o]\s*FACTURE)\s*[:\-]?\s*([A-Z0-9\-/]+)", re.IGNORECASE)
DATE_PATTERN = re.compile(r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b")
CODE_DGID_PATTERN = re.compile(
    r"(?:CODE\s+DE\s+VALIDATION|VALIDATION\s+DGID|N[°o]?\s*VALIDATION)\s*[:\-]?\s*([A-Z0-9\-]{6,})", re.IGNORECASE
)
LIGNE_ARTICLE_PATTERN = re.compile(
    r"^(?P<designation>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9 '\-\.]{2,60}?)\s+"
    r"(?P<quantite>\d+(?:[.,]\d+)?)\s+(?:x\s*)?"
    r"(?P<prix>[\d][\d\s.,]*\d|\d)\s*(?:FCFA)?$",
    re.IGNORECASE,
)


class OcrIndisponibleError(Exception):
    """Levee quand le binaire Tesseract n'est pas installe sur la machine (l'OCR est
    requis pour lire ce document : PDF scanne sans texte natif, ou image)."""


def parser_montant(brut: str) -> Decimal | None:
    """"1 234 567,89", "1234567.89" ou "1.234.567" -> Decimal. None si illisible."""
    nettoye = re.sub(r"[^\d.,]", "", brut)
    if not nettoye:
        return None

    if "," in nettoye and "." in nettoye:
        if nettoye.rfind(",") > nettoye.rfind("."):
            nettoye = nettoye.replace(".", "").replace(",", ".")
        else:
            nettoye = nettoye.replace(",", "")
    elif "," in nettoye:
        derniere_partie = nettoye.rsplit(",", 1)[1]
        if nettoye.count(",") == 1 and len(derniere_partie) in (1, 2):
            nettoye = nettoye.replace(",", ".")
        else:
            nettoye = nettoye.replace(",", "")
    elif "." in nettoye:
        derniere_partie = nettoye.rsplit(".", 1)[1]
        if nettoye.count(".") != 1 or len(derniere_partie) not in (1, 2):
            nettoye = nettoye.replace(".", "")

    try:
        return Decimal(nettoye)
    except InvalidOperation:
        return None


def _est_pdf(contenu: bytes, content_type: str | None) -> bool:
    return content_type == "application/pdf" or contenu[:4] == b"%PDF"


def extraire_texte_document(contenu: bytes, content_type: str | None) -> tuple[str, bool]:
    """Retourne (texte, via_ocr). Pour un PDF : texte natif prefere, fallback OCR page par
    page si trop peu de texte natif est trouve. Pour une image : OCR direct.

    Leve OcrIndisponibleError si l'OCR est necessaire mais que le binaire Tesseract est
    absent. Ne leve jamais d'autre exception : un PDF illisible degrade vers une chaine
    vide plutot que de faire planter l'appelant."""
    if _est_pdf(contenu, content_type):
        try:
            with pdfplumber.open(io.BytesIO(contenu)) as pdf:
                texte_natif = "\n".join(page.extract_text() or "" for page in pdf.pages)
                if len(texte_natif.strip()) >= SEUIL_TEXTE_NATIF:
                    return texte_natif, False

                try:
                    import pytesseract
                except ImportError:
                    return texte_natif, False

                try:
                    texte_ocr = "\n".join(
                        pytesseract.image_to_string(page.to_image(resolution=200).original, lang="fra+eng")
                        for page in pdf.pages
                    )
                except pytesseract.TesseractNotFoundError as exc:
                    raise OcrIndisponibleError(
                        "Ce PDF est un scan sans texte natif : la lecture automatique necessite l'OCR "
                        "(Tesseract), qui n'est pas installe sur ce serveur."
                    ) from exc
        except OcrIndisponibleError:
            raise
        except Exception:
            return "", False

        if len(texte_ocr.strip()) > len(texte_natif.strip()):
            return texte_ocr, True
        return texte_natif, False

    # Image (jpg/png/heic converti, etc.)
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise OcrIndisponibleError(
            "La lecture automatique d'une image necessite l'OCR (Tesseract), qui n'est pas "
            "installe sur ce serveur."
        ) from exc

    try:
        image = Image.open(io.BytesIO(contenu))
        return pytesseract.image_to_string(image, lang="fra+eng"), True
    except pytesseract.TesseractNotFoundError as exc:
        raise OcrIndisponibleError(
            "La lecture automatique d'une image necessite l'OCR (Tesseract), qui n'est pas "
            "installe sur ce serveur."
        ) from exc
    except Exception:
        return "", True
