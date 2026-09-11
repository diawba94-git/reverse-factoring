import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.enums import RoleUtilisateur, StatutTicket
from app.models.ticket_support import TicketSupport
from app.models.utilisateur import Utilisateur
from app.schemas.ticket_support import TicketSupportCreate, TicketSupportOut, TicketSupportUpdate
from app.services.audit import enregistrer_audit

router = APIRouter(prefix="/tickets-support", tags=["tickets-support"])

_ROLES_SUPPORT = [RoleUtilisateur.ADMIN]


def _get_ticket_or_404(db: Session, ticket_id: uuid.UUID) -> TicketSupport:
    ticket = db.get(TicketSupport, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket introuvable")
    return ticket


@router.post("", response_model=TicketSupportOut, status_code=status.HTTP_201_CREATED)
def creer_ticket(
    payload: TicketSupportCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    ticket = TicketSupport(
        entreprise_id=current_user.entreprise_id,
        utilisateur_id=current_user.id,
        sujet=payload.sujet,
        description=payload.description,
        priorite=payload.priorite,
    )
    db.add(ticket)
    db.flush()
    enregistrer_audit(
        db,
        entite_type="TicketSupport",
        entite_id=ticket.id,
        action="creation",
        utilisateur_id=current_user.id,
        valeur_apres={"sujet": ticket.sujet},
    )
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("", response_model=list[TicketSupportOut])
def lister_tickets(
    statut: StatutTicket | None = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    query = db.query(TicketSupport)
    if current_user.role not in _ROLES_SUPPORT:
        query = query.filter(TicketSupport.entreprise_id == current_user.entreprise_id)
    if statut is not None:
        query = query.filter(TicketSupport.statut == statut)
    return query.order_by(TicketSupport.date_creation.desc()).all()


@router.get("/{ticket_id}", response_model=TicketSupportOut)
def obtenir_ticket(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    ticket = _get_ticket_or_404(db, ticket_id)
    if current_user.role not in _ROLES_SUPPORT and ticket.entreprise_id != current_user.entreprise_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse a ce ticket")
    return ticket


@router.put("/{ticket_id}", response_model=TicketSupportOut)
def modifier_ticket(
    ticket_id: uuid.UUID,
    payload: TicketSupportUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_SUPPORT)),
):
    ticket = _get_ticket_or_404(db, ticket_id)
    avant = {"statut": ticket.statut.value, "priorite": ticket.priorite}
    changements = payload.model_dump(exclude_unset=True)
    for field, value in changements.items():
        setattr(ticket, field, value)

    if "statut" in changements and changements["statut"] in (StatutTicket.RESOLU, StatutTicket.FERME):
        ticket.date_resolution = datetime.now(timezone.utc)

    enregistrer_audit(
        db,
        entite_type="TicketSupport",
        entite_id=ticket.id,
        action="modification",
        utilisateur_id=current_user.id,
        valeur_avant=avant,
        valeur_apres=payload.model_dump(exclude_unset=True, mode="json"),
    )
    db.commit()
    db.refresh(ticket)
    return ticket


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_ticket(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role([RoleUtilisateur.ADMIN])),
):
    ticket = _get_ticket_or_404(db, ticket_id)
    db.delete(ticket)
    enregistrer_audit(
        db,
        entite_type="TicketSupport",
        entite_id=ticket.id,
        action="suppression",
        utilisateur_id=current_user.id,
        valeur_apres={"sujet": ticket.sujet},
    )
    db.commit()
