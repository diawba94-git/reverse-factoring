import uuid
from decimal import Decimal

from pydantic import BaseModel


class DonneurOrdrePortefeuilleOut(BaseModel):
    donneur_ordre_id: uuid.UUID
    raison_sociale: str
    encours: Decimal
    limite_plafond: Decimal | None
    limite_utilisee: Decimal | None
    retards: int


class PmeFinanceeOut(BaseModel):
    pme_id: uuid.UUID
    raison_sociale: str
    ninea: str | None
    encours: Decimal
    nombre_factures: int


class AcheteurPartenaireOut(BaseModel):
    donneur_ordre_id: uuid.UUID
    raison_sociale: str
    secteur_activite: str | None
    encours: Decimal
    taux_retard: Decimal
