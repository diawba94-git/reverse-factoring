import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.enums import RoleUtilisateur
from app.models.facture import Facture
from app.models.message_facture import MessageFacture
from app.models.utilisateur import Utilisateur
from app.schemas.message_facture import MessageFactureCreate, MessageFactureOut
from app.services.roles import ROLES_VALIDATEURS

router = APIRouter(prefix="/factures/{facture_id}/messages", tags=["messages"])

_ROLES_SUPERVISION = {RoleUtilisateur.AGENT_FINANCIER, RoleUtilisateur.ADMIN}


def _get_facture_avec_acces(db: Session, facture_id: uuid.UUID, current_user: Utilisateur) -> Facture:
    facture = db.get(Facture, facture_id)
    if facture is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facture introuvable")

    if current_user.role in _ROLES_SUPERVISION:
        return facture

    autorise = (
        (current_user.role == RoleUtilisateur.MEMBRE_PME and facture.pme_id == current_user.entreprise_id)
        or (
            current_user.role in ROLES_VALIDATEURS
            and facture.donneur_ordre_id == current_user.entreprise_id
        )
    )
    if not autorise:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse a cette facture")
    return facture


@router.get("", response_model=list[MessageFactureOut])
def lister_messages(
    facture_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    _get_facture_avec_acces(db, facture_id, current_user)
    return (
        db.query(MessageFacture)
        .filter(MessageFacture.facture_id == facture_id)
        .order_by(MessageFacture.date_envoi.asc())
        .all()
    )


@router.post("", response_model=MessageFactureOut, status_code=status.HTTP_201_CREATED)
def envoyer_message(
    facture_id: uuid.UUID,
    payload: MessageFactureCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    _get_facture_avec_acces(db, facture_id, current_user)
    message = MessageFacture(facture_id=facture_id, utilisateur_id=current_user.id, contenu=payload.contenu)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message
