import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import MotifAvoir, StatutAvoir, StatutCreance
from app.schemas.common import ORMBase


class AvoirCreate(BaseModel):
    montant_ht: Decimal
    montant_tva: Decimal
    montant_ttc: Decimal
    motif: MotifAvoir
    piece_justificative_url: str | None = None


class AvoirOut(ORMBase):
    id: uuid.UUID
    numero_avoir: str
    facture_id: uuid.UUID
    montant_ht: Decimal
    montant_tva: Decimal
    montant_ttc: Decimal
    motif: MotifAvoir
    statut: StatutAvoir
    date_emission: date
    piece_justificative_url: str | None
    effet_applique: str | None
    montant_deduit_solde: Decimal | None
    created_at: datetime


class CreanceOut(ORMBase):
    id: uuid.UUID
    pme_id: uuid.UUID
    avoir_id: uuid.UUID
    montant_du: Decimal
    montant_recouvre: Decimal
    statut: StatutCreance
    date_creation: datetime
