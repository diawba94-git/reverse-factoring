from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class NotificationPartenaireOut(BaseModel):
    type: str
    titre: str
    description: str
    date: datetime
    lu: bool


class VolumeMoisOut(BaseModel):
    mois: str
    montant: Decimal


class RapportResumeOut(BaseModel):
    volume_par_mois: list[VolumeMoisOut]
    montant_finance_ce_mois: Decimal
    variation_montant_finance_pct: Decimal | None
    frais_generes_ce_mois: Decimal
    variation_frais_generes_pct: Decimal | None
    rendement_portefeuille_pct: Decimal
