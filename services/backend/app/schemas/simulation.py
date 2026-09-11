import uuid
from decimal import Decimal

from pydantic import BaseModel, Field


class SimulationFraisRequest(BaseModel):
    montant: Decimal = Field(gt=0)
    duree_jours: int = Field(gt=0)
    grille_tarifaire_id: uuid.UUID | None = None


class SimulationFraisResponse(BaseModel):
    montant_avance_initial: Decimal
    montant_solde_du: Decimal
    frais_total: Decimal
    taeg_annualise: Decimal
    grille_utilisee: str
