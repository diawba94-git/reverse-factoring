import uuid
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import TypeLimite
from app.schemas.common import ORMBase


class LimiteCreditCreate(BaseModel):
    partenaire_financier_id: uuid.UUID
    entreprise_cible_id: uuid.UUID
    type_limite: TypeLimite
    montant_plafond: Decimal


class LimiteCreditUpdate(BaseModel):
    montant_plafond: Decimal | None = None
    active: bool | None = None


class LimiteCreditOut(ORMBase):
    id: uuid.UUID
    partenaire_financier_id: uuid.UUID
    entreprise_cible_id: uuid.UUID
    type_limite: TypeLimite
    montant_plafond: Decimal
    montant_utilise: Decimal
    active: bool
