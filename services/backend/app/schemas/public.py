from decimal import Decimal

from pydantic import BaseModel


class PublicStatsOut(BaseModel):
    """Statistiques agregees affichees avant connexion (page de connexion) — aucune donnee
    sensible, uniquement des compteurs et un total, jamais d'information nominative."""

    pme_actives: int
    acheteurs_actifs: int
    volume_finance_total: Decimal
