"""Logique de compensation d'un avoir confirme (architecture-mvp §3.0sexies) : selon le
statut de la Facture au moment de la confirmation (jamais a la simple creation d'un avoir,
qui reste une proposition en attente tant que l'acheteur ne l'a pas confirmee — voir
POST /avoirs/{id}/confirmer), reduit soit directement la Facture, soit le solde restant du
de l'Avance deja versee, en creant une CreanceCompensation pour le reliquat non couvert par
ce solde."""

import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.avance import Avance
from app.models.avoir_facture import AvoirFacture
from app.models.creance_compensation import CreanceCompensation
from app.models.enums import StatutAvance, StatutCreance, StatutFacture
from app.models.facture import Facture

_STATUTS_FACTURE_NON_AVANCEE = {StatutFacture.EMISE, StatutFacture.VALIDEE, StatutFacture.AVANCE_DEMANDEE}
_STATUTS_FACTURE_AVANCEE = {StatutFacture.AVANCE_VERSEE, StatutFacture.SOLDEE}


def appliquer_avoir(db: Session, avoir: AvoirFacture, facture: Facture, avance: Avance | None) -> dict:
    """Applique l'effet de compensation. Renseigne avoir.effet_applique (et
    avoir.montant_deduit_solde le cas echeant) pour que annuler_effet_avoir puisse tout
    remettre a l'etat anterieur exact au rejet, sans avoir a re-deviner ce qui a change."""
    if facture.statut in _STATUTS_FACTURE_NON_AVANCEE:
        facture.montant_ttc -= avoir.montant_ttc
        avoir.effet_applique = "montant_facture_reduit"
        return {"effet": "montant_facture_reduit", "creance_generee": False}

    if facture.statut in _STATUTS_FACTURE_AVANCEE:
        if avance is None:
            raise ValueError("Facture avancee sans Avance associee : etat incoherent.")
        solde_disponible = avance.montant_solde_du if avance.statut != StatutAvance.SOLDEE else Decimal("0")
        if avoir.montant_ttc <= solde_disponible:
            avance.montant_solde_du -= avoir.montant_ttc
            avoir.effet_applique = "solde_reduit"
            avoir.montant_deduit_solde = avoir.montant_ttc
            return {"effet": "solde_reduit", "creance_generee": False}

        ecart = avoir.montant_ttc - solde_disponible
        avoir.montant_deduit_solde = solde_disponible
        avance.montant_solde_du = Decimal("0")
        creance = CreanceCompensation(
            pme_id=facture.pme_id,
            avoir_id=avoir.id,
            montant_du=ecart,
            statut=StatutCreance.EN_ATTENTE,
        )
        db.add(creance)
        avoir.effet_applique = "creance_creee"
        return {"effet": "creance_creee", "creance_generee": True, "creance": creance}

    raise ValueError(f"Impossible d'appliquer un avoir sur une facture au statut '{facture.statut.value}'.")


def annuler_effet_avoir(db: Session, avoir: AvoirFacture, facture: Facture, avance: Avance | None) -> None:
    """Remet Facture/Avance/CreanceCompensation a l'etat anterieur a la confirmation (appele
    au rejet — voir POST /avoirs/{id}/rejeter). Ne fait rien si aucun effet n'avait encore
    ete applique (rejet d'un avoir jamais confirme)."""
    if avoir.effet_applique == "montant_facture_reduit":
        facture.montant_ttc += avoir.montant_ttc
    elif avoir.effet_applique in ("solde_reduit", "creance_creee"):
        if avance is not None and avoir.montant_deduit_solde is not None:
            avance.montant_solde_du += avoir.montant_deduit_solde
        if avoir.effet_applique == "creance_creee" and avoir.creance is not None:
            db.delete(avoir.creance)

    avoir.effet_applique = None
    avoir.montant_deduit_solde = None


def get_creances_actives(db: Session, pme_id: uuid.UUID) -> list[CreanceCompensation]:
    return (
        db.query(CreanceCompensation)
        .filter(
            CreanceCompensation.pme_id == pme_id,
            CreanceCompensation.statut.in_([StatutCreance.EN_ATTENTE, StatutCreance.PARTIELLEMENT_RECOUVREE]),
        )
        .order_by(CreanceCompensation.date_creation.asc())
        .all()
    )


def verifier_et_deduire_creances(db: Session, pme_id: uuid.UUID, montant_a_verser: Decimal) -> Decimal:
    """A appeler avant tout versement a une PME (avance initiale ou solde) : deduit en
    priorite toute creance en attente/partiellement recouvree, quelle que soit la facture ou
    le donneur d'ordre concerne par le nouveau versement — une creance en attente est
    toujours prioritaire. Retourne le montant reellement verse a la PME apres deduction."""
    creances = get_creances_actives(db, pme_id)
    for creance in creances:
        montant_restant_creance = creance.montant_du - creance.montant_recouvre
        deduction = min(montant_restant_creance, montant_a_verser)
        if deduction <= 0:
            continue
        creance.montant_recouvre += deduction
        montant_a_verser -= deduction
        creance.statut = (
            StatutCreance.SOLDEE
            if creance.montant_recouvre >= creance.montant_du
            else StatutCreance.PARTIELLEMENT_RECOUVREE
        )
        if montant_a_verser <= 0:
            break
    return montant_a_verser
