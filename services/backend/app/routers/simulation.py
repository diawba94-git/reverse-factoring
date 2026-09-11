from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.utilisateur import Utilisateur
from app.schemas.simulation import SimulationFraisRequest, SimulationFraisResponse
from app.services.calcul_frais import DureeInsuffisanteError, TaegDepasseError, calculer_frais
from app.services.grille import obtenir_grille_active

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.post("/frais", response_model=SimulationFraisResponse)
def simuler_frais(
    payload: SimulationFraisRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    grille = obtenir_grille_active(db, payload.grille_tarifaire_id)

    try:
        resultat = calculer_frais(payload.montant, payload.duree_jours, grille)
    except DureeInsuffisanteError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TaegDepasseError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return SimulationFraisResponse(
        montant_avance_initial=resultat.montant_avance_initial,
        montant_solde_du=resultat.montant_solde_du,
        frais_total=resultat.frais_total,
        taeg_annualise=resultat.taeg_annualise,
        grille_utilisee=grille.nom,
    )
