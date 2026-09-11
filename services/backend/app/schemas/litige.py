import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import ActionLitige, CauseLitige, StatutLitige


class LitigeCreate(BaseModel):
    facture_id: uuid.UUID
    cause: CauseLitige
    montant_en_jeu: Decimal
    description: str


class LitigeActionRequest(BaseModel):
    action: ActionLitige
    resolution_note: str | None = None


class LitigeOut(BaseModel):
    id: uuid.UUID
    facture_id: uuid.UUID
    numero_facture: str | None
    fournisseur: str
    acheteur: str
    partenaire_concerne: str | None
    cause: CauseLitige
    montant_en_jeu: Decimal
    description: str
    statut: StatutLitige
    derniere_action: str | None
    resolution_note: str | None
    ouvert_le: datetime
    resolu_le: datetime | None
