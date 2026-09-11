"""Pre-remplissage assiste du formulaire de creation de facture (PME) a partir d'un
fichier existant (PDF ou photo/scan image) : extrait au mieux les dates, le taux de TVA,
les montants et les lignes d'articles pour eviter une ressaisie manuelle complete.

A la difference du controle de conformite (app.services.conformite_facture, qui exige une
correspondance exacte avec le NINEA declare avant d'accepter une facture), ce module ne
sert qu'a produire un brouillon : aucune valeur extraite n'est jamais appliquee sans
relecture explicite par l'utilisateur cote frontend.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.services.extraction_texte_facture import (
    DATE_PATTERN,
    LIGNE_ARTICLE_PATTERN,
    MONTANT_HT_PATTERN,
    MONTANT_TTC_PATTERN,
    MONTANT_TVA_PATTERN,
    NUMERO_FACTURE_PATTERN,
    TAUX_TVA_PATTERN,
    extraire_texte_document,
    parser_montant,
)

_MOTS_CLES_ECHEANCE = ("echeance", "échéance", "date limite", "payer avant", "due date")


@dataclass
class LigneExtraite:
    designation: str
    quantite: Decimal
    prix_unitaire: Decimal


@dataclass
class ExtractionFactureImport:
    texte_brut: str
    via_ocr: bool
    numero_facture: str | None = None
    date_emission: date | None = None
    date_echeance: date | None = None
    taux_tva: Decimal | None = None
    montant_ht: Decimal | None = None
    montant_tva: Decimal | None = None
    montant_ttc: Decimal | None = None
    lignes: list[LigneExtraite] = field(default_factory=list)
    avertissements: list[str] = field(default_factory=list)


def _parser_date(brut: str) -> date | None:
    brut = brut.replace(".", "/").replace("-", "/")
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(brut, fmt).date()
        except ValueError:
            continue
    return None


def _extraire_dates(texte: str) -> tuple[date | None, date | None]:
    """Premiere date trouvee = emission. La date la plus proche APRES un mot-cle
    d'echeance (motif « libelle : date ») est retenue en priorite ; a defaut, une date
    trouvee juste avant le mot-cle (motif inverse, fenetre etroite pour eviter de
    reprendre la date d'emission d'une ligne precedente) ; a defaut, la derniere date
    distincte du document si plusieurs dates sont presentes."""
    correspondances = list(DATE_PATTERN.finditer(texte))
    dates_valides = [(m.start(), _parser_date(m.group(1))) for m in correspondances]
    dates_valides = [(pos, d) for pos, d in dates_valides if d is not None]
    if not dates_valides:
        return None, None

    emission = dates_valides[0][1]

    texte_minuscule = texte.lower()
    for mot_cle in _MOTS_CLES_ECHEANCE:
        idx = texte_minuscule.find(mot_cle)
        if idx == -1:
            continue
        apres = sorted((pos, d) for pos, d in dates_valides if 0 <= pos - idx < 40)
        if apres:
            return emission, apres[0][1]
        avant = sorted(((pos, d) for pos, d in dates_valides if 0 <= idx - pos < 15), reverse=True)
        if avant:
            return emission, avant[0][1]

    distinctes = [d for _, d in dates_valides if d != emission]
    if distinctes:
        return emission, distinctes[-1]
    return emission, None


def _chercher_montant_plausible(pattern, texte: str, seuil: Decimal = Decimal("100")) -> Decimal | None:
    """Comme pattern.search(texte) puis parser_montant, mais ignore les correspondances
    dont le nombre capture est trop petit pour etre un montant FCFA plausible — cas
    frequent quand le groupe optionnel de pourcentage du motif n'est pas suivi d'un
    montant sur la meme ligne (ex: une ligne "TVA 18%" isolee, sans le montant en FCFA
    associe, qui capture alors "18" au lieu du montant recherche plus loin)."""
    for m in pattern.finditer(texte):
        valeur = parser_montant(m.group(1))
        if valeur is not None and valeur >= seuil:
            return valeur
    return None


def _extraire_lignes(texte: str) -> list[LigneExtraite]:
    """Detection heuristique de lignes d'articles au format
    « designation  quantite  prix_unitaire » (le format le plus courant sur une facture
    tabulaire une fois le texte linearise par l'OCR/l'extraction PDF). Best-effort
    uniquement : toujours presente comme un brouillon a corriger, jamais une verite
    definitive."""
    lignes: list[LigneExtraite] = []
    for ligne_texte in texte.splitlines():
        ligne_texte = ligne_texte.strip()
        if not ligne_texte:
            continue
        m = LIGNE_ARTICLE_PATTERN.match(ligne_texte)
        if not m:
            continue
        quantite = parser_montant(m.group("quantite"))
        prix = parser_montant(m.group("prix"))
        designation = m.group("designation").strip()
        if quantite is None or prix is None or not designation:
            continue
        # Evite de confondre une ligne "Montant HT  1234567" avec un article.
        if designation.lower() in {"montant ht", "montant tva", "montant ttc", "total", "sous-total", "total ht", "total ttc"}:
            continue
        lignes.append(LigneExtraite(designation=designation, quantite=quantite, prix_unitaire=prix))
    return lignes[:20]


def extraire_brouillon_facture(contenu: bytes, content_type: str | None) -> ExtractionFactureImport:
    """Ne leve jamais d'exception liee au contenu du document : un document illisible ou
    sans aucun champ reconnaissable retourne un brouillon vide (charge a l'utilisateur de
    saisir manuellement). Seule OcrIndisponibleError (cf. extraction_texte_facture) est
    laissee remonter : c'est une erreur d'infrastructure, pas un probleme de document."""
    texte, via_ocr = extraire_texte_document(contenu, content_type)

    resultat = ExtractionFactureImport(texte_brut=texte, via_ocr=via_ocr)
    if not texte.strip():
        resultat.avertissements.append("Aucun texte n'a pu être extrait de ce document — remplissez le formulaire manuellement.")
        return resultat

    if via_ocr:
        resultat.avertissements.append(
            "Ce document a été lu par reconnaissance optique (OCR) : vérifiez attentivement les champs ci-dessous avant de continuer."
        )

    m = NUMERO_FACTURE_PATTERN.search(texte)
    if m:
        resultat.numero_facture = m.group(1).strip()

    resultat.date_emission, resultat.date_echeance = _extraire_dates(texte)
    if resultat.date_emission and not resultat.date_echeance:
        resultat.avertissements.append("Une seule date a été trouvée — vérifiez la date d'échéance.")

    m = TAUX_TVA_PATTERN.search(texte)
    if m:
        try:
            resultat.taux_tva = Decimal(m.group(1).replace(",", ".")) / Decimal("100")
        except InvalidOperation:
            resultat.taux_tva = None

    resultat.montant_ht = _chercher_montant_plausible(MONTANT_HT_PATTERN, texte)
    resultat.montant_tva = _chercher_montant_plausible(MONTANT_TVA_PATTERN, texte)
    resultat.montant_ttc = _chercher_montant_plausible(MONTANT_TTC_PATTERN, texte)

    resultat.lignes = _extraire_lignes(texte)
    if not resultat.lignes:
        resultat.avertissements.append("Aucune ligne d'article n'a été détectée — ajoutez-les manuellement à l'étape suivante.")

    return resultat
