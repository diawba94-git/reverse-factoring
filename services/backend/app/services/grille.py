import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.grille_tarifaire import GrilleTarifaire


def obtenir_grille_active(db: Session, grille_tarifaire_id: uuid.UUID | None = None) -> GrilleTarifaire:
    if grille_tarifaire_id is not None:
        grille = db.get(GrilleTarifaire, grille_tarifaire_id)
        if grille is None or not grille.active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Grille tarifaire introuvable ou inactive"
            )
        return grille

    grille = (
        db.query(GrilleTarifaire)
        .filter(GrilleTarifaire.active.is_(True))
        .filter(GrilleTarifaire.date_debut_validite <= date.today())
        .filter((GrilleTarifaire.date_fin_validite.is_(None)) | (GrilleTarifaire.date_fin_validite >= date.today()))
        .order_by(GrilleTarifaire.date_debut_validite.desc())
        .first()
    )
    if grille is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucune grille tarifaire active")
    return grille
