"""Meme controle de continuite que app.services.numerotation_facture (numero sans trou ni
doublon par PME), applique a la sequence des avoirs — independante de celle des factures.
AvoirFacture n'a pas de pme_id propre : la sequence se lit via un join sur Facture."""

import re
import uuid

from sqlalchemy.orm import Session

from app.models.avoir_facture import AvoirFacture
from app.models.facture import Facture

_SUFFIXE_NUMERIQUE = re.compile(r"^(.*?)(\d+)$")


class SequenceAvoirRompueError(ValueError):
    pass


def _decomposer(numero_avoir: str) -> tuple[str, int, int]:
    m = _SUFFIXE_NUMERIQUE.match(numero_avoir)
    if not m:
        raise SequenceAvoirRompueError(
            "Le numero d'avoir doit se terminer par une suite de chiffres pour permettre "
            "la verification de la continuite de la sequence (ex: AV-2026-0004)."
        )
    prefixe, suffixe = m.group(1), m.group(2)
    return prefixe, int(suffixe), len(suffixe)


def generer_prochain_numero(db: Session, pme_id: uuid.UUID, annee: int) -> str:
    """Attribue le prochain numero de la sequence `AV-{annee}-NNNN` de cette PME (jamais
    saisi par l'utilisateur). Tous les avoirs deja numerotes sous ce prefixe comptent, quel
    que soit leur statut (y compris rejete), pour garantir l'absence de trou."""
    prefixe = f"AV-{annee}-"
    largeur = 4

    candidats = (
        db.query(AvoirFacture.numero_avoir)
        .join(Facture, Facture.id == AvoirFacture.facture_id)
        .filter(Facture.pme_id == pme_id, AvoirFacture.numero_avoir.like(f"{prefixe}%"))
        .all()
    )

    derniere_valeur = 0
    for (numero,) in candidats:
        try:
            candidat_prefixe, candidat_valeur, candidat_largeur = _decomposer(numero)
        except ValueError:
            continue
        if candidat_prefixe != prefixe:
            continue
        derniere_valeur = max(derniere_valeur, candidat_valeur)
        largeur = max(largeur, candidat_largeur)

    return f"{prefixe}{derniere_valeur + 1:0{largeur}d}"
