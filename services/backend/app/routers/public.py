from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.avance import Avance
from app.models.entreprise import Entreprise
from app.models.enums import StatutAvance, StatutFiche, TypeEntreprise
from app.schemas.public import PublicStatsOut

router = APIRouter(prefix="/public", tags=["public"])


@router.get(
    "/stats",
    response_model=PublicStatsOut,
    summary="Statistiques agregees affichees avant connexion (page de connexion) — sans authentification",
)
def obtenir_stats_publiques(db: Session = Depends(get_db)):
    pme_actives = (
        db.query(Entreprise)
        .filter(Entreprise.type == TypeEntreprise.PME, Entreprise.statut_fiche == StatutFiche.ACTIVE, Entreprise.actif.is_(True))
        .count()
    )
    acheteurs_actifs = (
        db.query(Entreprise)
        .filter(
            Entreprise.type == TypeEntreprise.GRANDE_ENTREPRISE,
            Entreprise.statut_fiche == StatutFiche.ACTIVE,
            Entreprise.actif.is_(True),
        )
        .count()
    )
    volume_finance_total = (
        db.query(func.coalesce(func.sum(Avance.montant_avance_initial), 0))
        .filter(Avance.statut.in_([StatutAvance.AVANCE_VERSEE, StatutAvance.SOLDEE]))
        .scalar()
    )

    return PublicStatsOut(
        pme_actives=pme_actives,
        acheteurs_actifs=acheteurs_actifs,
        volume_finance_total=Decimal(volume_finance_total),
    )
