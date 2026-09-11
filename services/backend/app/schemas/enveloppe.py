import uuid
from decimal import Decimal

from pydantic import BaseModel


class EnveloppeOut(BaseModel):
    partenaire_financier_id: uuid.UUID
    montant_total_alloue: Decimal
    montant_engage: Decimal
    montant_disponible: Decimal


class EnveloppeUpdate(BaseModel):
    montant_total_alloue: Decimal
