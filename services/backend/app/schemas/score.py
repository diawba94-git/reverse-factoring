import uuid
from datetime import datetime
from decimal import Decimal

from app.schemas.common import ORMBase


class ScoreDonneurOrdreOut(ORMBase):
    id: uuid.UUID
    entreprise_id: uuid.UUID
    score: Decimal
    facteurs_positifs: dict
    facteurs_negatifs: dict
    modele_version: str
    date_calcul: datetime
    calculee_par: str
