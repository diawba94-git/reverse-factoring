import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import StatutTicket
from app.schemas.common import ORMBase


class TicketSupportCreate(BaseModel):
    sujet: str
    description: str
    priorite: str = "normale"


class TicketSupportUpdate(BaseModel):
    statut: StatutTicket | None = None
    priorite: str | None = None


class TicketSupportOut(ORMBase):
    id: uuid.UUID
    entreprise_id: uuid.UUID
    utilisateur_id: uuid.UUID
    sujet: str
    description: str
    statut: StatutTicket
    priorite: str
    date_creation: datetime
    date_resolution: datetime | None
