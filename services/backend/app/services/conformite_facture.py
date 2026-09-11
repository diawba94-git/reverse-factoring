"""Controle de conformite automatique d'une facture PDF senegalaise : extraction des
mentions obligatoires (NINEA de l'emetteur, montants HT/TVA/TTC, numero, date, code de
validation DGID) et verification de leur coherence avant qu'une facture puisse etre
emise.

Limite connue : quand le PDF ne contient aucune couche de texte native (scan pur), la
lecture bascule sur l'OCR (pytesseract), nettement moins fiable qu'une extraction de
texte native (confusions frequentes entre chiffres, espaces et separateurs) ; un
avertissement est alors ajoute au resultat pour le signaler explicitement a l'appelant.
Le "code de validation DGID" n'est lu ici que sous sa forme texte imprimee sur la
facture (pas de decodage de QR code : cela demanderait une bibliotheque de lecture de
code-barres dediee, hors perimetre de cette premiere version).
"""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.models.entreprise import Entreprise
from app.services.extraction_texte_facture import (
    CODE_DGID_PATTERN as _CODE_DGID_PATTERN,
    MONTANT_HT_PATTERN as _MONTANT_HT_PATTERN,
    MONTANT_TTC_PATTERN as _MONTANT_TTC_PATTERN,
    MONTANT_TVA_PATTERN as _MONTANT_TVA_PATTERN,
    NINEA_PATTERN as _NINEA_PATTERN,
    NUMERO_FACTURE_PATTERN as _NUMERO_FACTURE_PATTERN,
    DATE_PATTERN as _DATE_PATTERN,
    TAUX_TVA_PATTERN as _TAUX_TVA_PATTERN,
    extraire_texte_document,
    parser_montant as _parser_montant,
)

_TOLERANCE_FCFA = Decimal("2.00")
_TAUX_TVA_DEFAUT = Decimal("0.18")


@dataclass
class ChampsExtraits:
    ninea_emetteur: str | None = None
    montant_ht: Decimal | None = None
    montant_tva: Decimal | None = None
    montant_ttc: Decimal | None = None
    taux_tva: Decimal | None = None
    numero_facture: str | None = None
    date_emission: str | None = None
    code_validation_dgid: str | None = None


@dataclass
class ResultatConformite:
    conforme: bool
    champs_extraits: ChampsExtraits
    motifs_rejet: list[str] = field(default_factory=list)
    avertissements: list[str] = field(default_factory=list)
    via_ocr: bool = False


def _extraire_champs(texte: str) -> ChampsExtraits:
    champs = ChampsExtraits()

    m = _NINEA_PATTERN.search(texte)
    if m:
        champs.ninea_emetteur = m.group(1).upper()

    m = _MONTANT_HT_PATTERN.search(texte)
    if m:
        champs.montant_ht = _parser_montant(m.group(1))

    m = _MONTANT_TVA_PATTERN.search(texte)
    if m:
        champs.montant_tva = _parser_montant(m.group(1))

    m = _MONTANT_TTC_PATTERN.search(texte)
    if m:
        champs.montant_ttc = _parser_montant(m.group(1))

    m = _TAUX_TVA_PATTERN.search(texte)
    if m:
        try:
            champs.taux_tva = Decimal(m.group(1).replace(",", ".")) / Decimal("100")
        except InvalidOperation:
            champs.taux_tva = None

    m = _NUMERO_FACTURE_PATTERN.search(texte)
    if m:
        champs.numero_facture = m.group(1).strip()

    m = _DATE_PATTERN.search(texte)
    if m:
        champs.date_emission = m.group(1)

    m = _CODE_DGID_PATTERN.search(texte)
    if m:
        champs.code_validation_dgid = m.group(1).strip()

    return champs


def verifier_conformite_facture(db: Session, contenu_pdf: bytes, pme_id: uuid.UUID) -> ResultatConformite:
    """entreprise emettrice (pme_id) : compare son NINEA declare a celui extrait du
    document. Ne leve jamais d'exception metier : toute erreur de lecture se traduit par
    un motif de rejet explicite dans le resultat, jamais par une 500."""
    entreprise = db.get(Entreprise, pme_id)

    try:
        texte, via_ocr = extraire_texte_document(contenu_pdf, "application/pdf")
    except Exception as exc:
        return ResultatConformite(
            conforme=False,
            champs_extraits=ChampsExtraits(),
            motifs_rejet=[f"Impossible de lire le document PDF ({exc})."],
        )

    champs = _extraire_champs(texte)
    motifs: list[str] = []
    avertissements: list[str] = []

    if via_ocr:
        avertissements.append(
            "Le texte du document a ete lu par reconnaissance optique (OCR) faute de texte "
            "natif dans le PDF : cette lecture est moins fiable qu'un PDF genere "
            "numeriquement, verifiez les montants extraits."
        )

    ninea_declare = (entreprise.ninea if entreprise else "").strip().upper()
    if champs.ninea_emetteur is None:
        motifs.append("NINEA introuvable sur le document.")
    elif champs.ninea_emetteur != ninea_declare:
        motifs.append("Le NINEA du document ne correspond pas au NINEA declare de votre entreprise.")

    if champs.montant_ht is None:
        motifs.append("Montant HT introuvable sur le document.")
    if champs.montant_tva is None:
        motifs.append("Montant TVA introuvable sur le document.")
    if champs.montant_ttc is None:
        motifs.append("Montant TTC introuvable sur le document.")

    taux = champs.taux_tva if champs.taux_tva is not None else _TAUX_TVA_DEFAUT
    if champs.montant_ht is not None and champs.montant_tva is not None:
        attendu_tva = (champs.montant_ht * taux).quantize(Decimal("0.01"))
        if abs(attendu_tva - champs.montant_tva) > _TOLERANCE_FCFA:
            motifs.append(
                f"Montant TVA incoherent avec le montant HT (attendu environ {attendu_tva} FCFA "
                f"au taux de {(taux * 100).normalize()}%, document indique {champs.montant_tva} FCFA)."
            )

    if champs.montant_ht is not None and champs.montant_tva is not None and champs.montant_ttc is not None:
        somme = champs.montant_ht + champs.montant_tva
        if abs(somme - champs.montant_ttc) > _TOLERANCE_FCFA:
            motifs.append(
                f"Montant TTC incoherent avec HT + TVA (attendu {somme} FCFA, document "
                f"indique {champs.montant_ttc} FCFA)."
            )

    return ResultatConformite(
        conforme=len(motifs) == 0,
        champs_extraits=champs,
        motifs_rejet=motifs,
        avertissements=avertissements,
        via_ocr=via_ocr,
    )
