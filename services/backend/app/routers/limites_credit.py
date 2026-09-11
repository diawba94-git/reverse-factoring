import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.enums import RoleUtilisateur
from app.models.limite_credit import LimiteCredit
from app.models.utilisateur import Utilisateur
from app.schemas.limite_credit import LimiteCreditCreate, LimiteCreditOut, LimiteCreditUpdate
from app.services.audit import enregistrer_audit

router = APIRouter(prefix="/limites-credit", tags=["limites-credit"])

_ROLE_AGENT = [RoleUtilisateur.AGENT_FINANCIER]


def _get_limite_or_404(db: Session, limite_id: uuid.UUID) -> LimiteCredit:
    limite = db.get(LimiteCredit, limite_id)
    if limite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Limite de credit introuvable")
    return limite


@router.post("", response_model=LimiteCreditOut, status_code=status.HTTP_201_CREATED)
def creer_limite(
    payload: LimiteCreditCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLE_AGENT)),
):
    limite = LimiteCredit(**payload.model_dump())
    db.add(limite)
    db.flush()
    enregistrer_audit(
        db,
        entite_type="LimiteCredit",
        entite_id=limite.id,
        action="creation",
        utilisateur_id=current_user.id,
        valeur_apres={"montant_plafond": str(limite.montant_plafond), "type_limite": limite.type_limite.value},
    )
    db.commit()
    db.refresh(limite)
    return limite


@router.get("", response_model=list[LimiteCreditOut])
def lister_limites(
    entreprise_cible_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLE_AGENT)),
):
    query = db.query(LimiteCredit).filter(LimiteCredit.partenaire_financier_id == current_user.entreprise_id)
    if entreprise_cible_id is not None:
        query = query.filter(LimiteCredit.entreprise_cible_id == entreprise_cible_id)
    return query.order_by(LimiteCredit.created_at.desc()).all()


@router.get("/{limite_id}", response_model=LimiteCreditOut)
def obtenir_limite(
    limite_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLE_AGENT)),
):
    return _get_limite_or_404(db, limite_id)


@router.put("/{limite_id}", response_model=LimiteCreditOut)
def modifier_limite(
    limite_id: uuid.UUID,
    payload: LimiteCreditUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLE_AGENT)),
):
    limite = _get_limite_or_404(db, limite_id)
    avant = {"montant_plafond": str(limite.montant_plafond), "active": limite.active}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(limite, field, value)

    enregistrer_audit(
        db,
        entite_type="LimiteCredit",
        entite_id=limite.id,
        action="modification",
        utilisateur_id=current_user.id,
        valeur_avant=avant,
        valeur_apres=payload.model_dump(exclude_unset=True, mode="json"),
    )
    db.commit()
    db.refresh(limite)
    return limite


@router.delete("/{limite_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_limite(
    limite_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLE_AGENT)),
):
    limite = _get_limite_or_404(db, limite_id)
    db.delete(limite)
    enregistrer_audit(
        db,
        entite_type="LimiteCredit",
        entite_id=limite.id,
        action="suppression",
        utilisateur_id=current_user.id,
        valeur_apres={"montant_plafond": str(limite.montant_plafond)},
    )
    db.commit()
