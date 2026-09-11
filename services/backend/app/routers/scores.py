import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.enums import RoleUtilisateur
from app.models.score_donneur_ordre import ScoreDonneurOrdre
from app.models.utilisateur import Utilisateur
from app.schemas.score import ScoreDonneurOrdreOut

router = APIRouter(prefix="/scores", tags=["scores"])


@router.get("/donneur-ordre/{entreprise_id}", response_model=ScoreDonneurOrdreOut)
def obtenir_score_donneur_ordre(
    entreprise_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role([RoleUtilisateur.AGENT_FINANCIER, RoleUtilisateur.ADMIN])),
):
    score = (
        db.query(ScoreDonneurOrdre)
        .filter(ScoreDonneurOrdre.entreprise_id == entreprise_id)
        .order_by(ScoreDonneurOrdre.date_calcul.desc())
        .first()
    )
    if score is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun score disponible pour ce donneur d'ordre")
    return score
