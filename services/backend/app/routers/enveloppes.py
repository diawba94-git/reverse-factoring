import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.avance import Avance
from app.models.entreprise import Entreprise
from app.models.enums import RoleUtilisateur, StatutAvance, TypeEntreprise
from app.models.enveloppe_partenaire import EnveloppePartenaire
from app.models.utilisateur import Utilisateur
from app.schemas.enveloppe import EnveloppeOut, EnveloppeUpdate

router = APIRouter(prefix="/enveloppes", tags=["enveloppes"])


def _calculer(db: Session, enveloppe: EnveloppePartenaire | None, partenaire_financier_id: uuid.UUID) -> EnveloppeOut:
    montant_engage = (
        db.query(func.coalesce(func.sum(Avance.montant_avance_initial), 0))
        .filter(Avance.partenaire_financier_id == partenaire_financier_id, Avance.statut == StatutAvance.AVANCE_VERSEE)
        .scalar()
    )
    total_alloue = enveloppe.montant_total_alloue if enveloppe else Decimal("0")
    return EnveloppeOut(
        partenaire_financier_id=partenaire_financier_id,
        montant_total_alloue=total_alloue,
        montant_engage=Decimal(montant_engage),
        montant_disponible=total_alloue - Decimal(montant_engage),
    )


@router.get("/moi", response_model=EnveloppeOut, summary="Enveloppe du partenaire connecte")
def mon_enveloppe(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role([RoleUtilisateur.AGENT_FINANCIER])),
):
    enveloppe = (
        db.query(EnveloppePartenaire)
        .filter(EnveloppePartenaire.partenaire_financier_id == current_user.entreprise_id)
        .first()
    )
    return _calculer(db, enveloppe, current_user.entreprise_id)


@router.get("/{partenaire_id}", response_model=EnveloppeOut, summary="Enveloppe d'un partenaire (admin uniquement)")
def obtenir_enveloppe(
    partenaire_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role([RoleUtilisateur.ADMIN])),
):
    enveloppe = db.query(EnveloppePartenaire).filter(EnveloppePartenaire.partenaire_financier_id == partenaire_id).first()
    return _calculer(db, enveloppe, partenaire_id)


@router.put(
    "/{partenaire_id}",
    response_model=EnveloppeOut,
    summary="Fixe le montant total alloue par un partenaire (admin uniquement)",
    description=(
        "Le montant total qu'un partenaire s'engage a financer, negocie contractuellement "
        "(doc §3.5.3) — les LimiteCredit plus fines restent configurables par le partenaire "
        "lui-meme dans son propre portefeuille."
    ),
)
def definir_enveloppe(
    partenaire_id: uuid.UUID,
    payload: EnveloppeUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role([RoleUtilisateur.ADMIN])),
):
    partenaire = db.get(Entreprise, partenaire_id)
    if partenaire is None or partenaire.type != TypeEntreprise.PARTENAIRE_FINANCIER:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partenaire financier introuvable")

    enveloppe = db.query(EnveloppePartenaire).filter(EnveloppePartenaire.partenaire_financier_id == partenaire_id).first()
    if enveloppe is None:
        enveloppe = EnveloppePartenaire(partenaire_financier_id=partenaire_id, montant_total_alloue=payload.montant_total_alloue)
        db.add(enveloppe)
    else:
        enveloppe.montant_total_alloue = payload.montant_total_alloue
    db.commit()
    return _calculer(db, enveloppe, partenaire_id)
