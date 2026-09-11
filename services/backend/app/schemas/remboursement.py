import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import StatutRapprochement
from app.schemas.common import ORMBase


class RemboursementCreate(BaseModel):
    avance_id: uuid.UUID
    montant_recu: Decimal
    date_reception: date
    source_entreprise_id: uuid.UUID


class RemboursementOut(ORMBase):
    id: uuid.UUID
    avance_id: uuid.UUID
    montant_recu: Decimal
    date_reception: date
    source_entreprise_id: uuid.UUID
    statut_rapprochement: StatutRapprochement
    declenche_versement_solde: bool


class RapprochementRequest(BaseModel):
    statut_rapprochement: StatutRapprochement
