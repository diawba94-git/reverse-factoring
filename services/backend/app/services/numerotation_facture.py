"""Verifie que le numero d'une nouvelle facture continue, sans trou ni doublon, la suite
numerique deja utilisee par la PME pour un meme prefixe (ex: "FA-2026-0147" ->
"FA-2026-0148"). Le format exact du numero est libre : seule la partie numerique finale
est comparee. Toutes les factures emises par la PME comptent dans la sequence, quel que
soit leur statut (y compris rejetee_conformite) : un numero une fois attribue n'est
jamais reutilisable, conformement a l'usage comptable standard."""

import re
import uuid

from sqlalchemy.orm import Session

from app.models.facture import Facture

_SUFFIXE_NUMERIQUE = re.compile(r"^(.*?)(\d+)$")


class SequenceRompueError(ValueError):
    """Distincte d'un ValueError generique pour que les endpoints puissent la mapper sur
    un 422 explicite, plutot que sur le 400 utilise pour les autres erreurs de saisie."""


def _decomposer(numero_facture: str) -> tuple[str, int, int]:
    """Retourne (prefixe, valeur_numerique, largeur_du_suffixe). Leve SequenceRompueError
    si le numero ne se termine pas par une suite de chiffres."""
    m = _SUFFIXE_NUMERIQUE.match(numero_facture)
    if not m:
        raise SequenceRompueError(
            "Le numero de facture doit se terminer par une suite de chiffres pour "
            "permettre la verification de la continuite de la sequence (ex: FA-2026-0148)."
        )
    prefixe, suffixe = m.group(1), m.group(2)
    return prefixe, int(suffixe), len(suffixe)


def generer_prochain_numero(db: Session, pme_id: uuid.UUID, annee: int) -> str:
    """Attribue le prochain numero de la sequence `FA-{annee}-NNNN` de cette PME (jamais
    saisi par l'utilisateur : voir POST /factures/{id}/transmettre). Comme pour la
    verification ci-dessus, toutes les factures deja numerotees sous ce prefixe comptent,
    quel que soit leur statut, pour garantir l'absence de trou."""
    prefixe = f"FA-{annee}-"
    largeur = 4

    candidats = (
        db.query(Facture.numero_facture)
        .filter(Facture.pme_id == pme_id, Facture.numero_facture.like(f"{prefixe}%"))
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


def verifier_numero_sequentiel(db: Session, pme_id: uuid.UUID, numero_facture: str) -> None:
    """Leve ValueError si numero_facture rompt la sequence de cette PME. Ne verifie que
    parmi les factures partageant le meme prefixe : changer de format de numerotation
    demarre simplement une nouvelle sequence."""
    prefixe, valeur, largeur = _decomposer(numero_facture)

    candidats = (
        db.query(Facture.numero_facture)
        .filter(Facture.pme_id == pme_id, Facture.numero_facture.like(f"{prefixe}%"))
        .all()
    )

    derniere_valeur: int | None = None
    for (numero,) in candidats:
        try:
            candidat_prefixe, candidat_valeur, _ = _decomposer(numero)
        except ValueError:
            continue
        if candidat_prefixe != prefixe:
            continue
        if derniere_valeur is None or candidat_valeur > derniere_valeur:
            derniere_valeur = candidat_valeur

    if derniere_valeur is None:
        return  # premiere facture sous ce prefixe : demarre la sequence

    if valeur != derniere_valeur + 1:
        attendu = f"{prefixe}{derniere_valeur + 1:0{largeur}d}"
        raise SequenceRompueError(
            f"Le numero de facture doit continuer la sequence sans interruption pour "
            f"cette entreprise. Dernier numero utilise : '{prefixe}{derniere_valeur:0{largeur}d}', "
            f"prochain numero attendu : '{attendu}'."
        )
