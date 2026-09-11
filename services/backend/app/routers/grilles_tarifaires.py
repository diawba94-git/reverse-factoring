import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.enums import RoleUtilisateur
from app.models.grille_tarifaire import GrilleTarifaire
from app.models.utilisateur import Utilisateur
from app.schemas.grille_tarifaire import GrilleTarifaireCreate, GrilleTarifaireOut, GrilleTarifaireUpdate
from app.services.audit import enregistrer_audit

router = APIRouter(prefix="/grilles-tarifaires", tags=["grilles-tarifaires"])

_ROLE_ADMIN = [RoleUtilisateur.ADMIN]


def _get_grille_or_404(db: Session, grille_id: uuid.UUID) -> GrilleTarifaire:
    grille = db.get(GrilleTarifaire, grille_id)
    if grille is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grille tarifaire introuvable")
    return grille


@router.post("", response_model=GrilleTarifaireOut, status_code=status.HTTP_201_CREATED)
def creer_grille(
    payload: GrilleTarifaireCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLE_ADMIN)),
):
    grille = GrilleTarifaire(**payload.model_dump())
    db.add(grille)
    db.flush()
    enregistrer_audit(
        db,
        entite_type="GrilleTarifaire",
        entite_id=grille.id,
        action="creation",
        utilisateur_id=current_user.id,
        valeur_apres={"nom": grille.nom, "taux_total_maximum": str(grille.taux_total_maximum)},
    )
    db.commit()
    db.refresh(grille)
    return grille


@router.get("/actives", response_model=list[GrilleTarifaireOut])
def lister_grilles_actives(db: Session = Depends(get_db)):
    today = date.today()
    return (
        db.query(GrilleTarifaire)
        .filter(GrilleTarifaire.active.is_(True))
        .filter(GrilleTarifaire.date_debut_validite <= today)
        .filter((GrilleTarifaire.date_fin_validite.is_(None)) | (GrilleTarifaire.date_fin_validite >= today))
        .order_by(GrilleTarifaire.date_debut_validite.desc())
        .all()
    )


@router.get("", response_model=list[GrilleTarifaireOut])
def lister_grilles(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLE_ADMIN)),
):
    return db.query(GrilleTarifaire).order_by(GrilleTarifaire.date_debut_validite.desc()).all()


@router.get("/{grille_id}", response_model=GrilleTarifaireOut)
def obtenir_grille(
    grille_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLE_ADMIN)),
):
    return _get_grille_or_404(db, grille_id)


@router.put("/{grille_id}", response_model=GrilleTarifaireOut)
def modifier_grille(
    grille_id: uuid.UUID,
    payload: GrilleTarifaireUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLE_ADMIN)),
):
    grille = _get_grille_or_404(db, grille_id)
    avant = {"taux_total_maximum": str(grille.taux_total_maximum), "active": grille.active}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(grille, field, value)

    enregistrer_audit(
        db,
        entite_type="GrilleTarifaire",
        entite_id=grille.id,
        action="modification",
        utilisateur_id=current_user.id,
        valeur_avant=avant,
        valeur_apres=payload.model_dump(exclude_unset=True, mode="json"),
    )
    db.commit()
    db.refresh(grille)
    return grille


@router.delete("/{grille_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_grille(
    grille_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLE_ADMIN)),
):
    grille = _get_grille_or_404(db, grille_id)
    db.delete(grille)
    enregistrer_audit(
        db,
        entite_type="GrilleTarifaire",
        entite_id=grille.id,
        action="suppression",
        utilisateur_id=current_user.id,
        valeur_apres={"nom": grille.nom},
    )
    db.commit()
