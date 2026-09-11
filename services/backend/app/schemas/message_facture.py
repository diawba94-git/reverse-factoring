import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMBase


class MessageFactureCreate(BaseModel):
    contenu: str


class MessageFactureOut(ORMBase):
    id: uuid.UUID
    facture_id: uuid.UUID
    utilisateur_id: uuid.UUID
    contenu: str
    date_envoi: datetime
    lu: bool
