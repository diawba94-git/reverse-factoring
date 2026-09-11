import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.enums import RoleUtilisateur
from app.models.journal_audit import JournalAudit
from app.models.utilisateur import Utilisateur
from app.schemas.utilisateur import UtilisateurCreate, UtilisateurOut, UtilisateurUpdate
from app.security import hash_password
from app.services.audit import enregistrer_audit

router = APIRouter(prefix="/utilisateurs", tags=["utilisateurs"])

_ROLES_ADMIN = [RoleUtilisateur.ADMIN]


def _get_utilisateur_or_404(db: Session, utilisateur_id: uuid.UUID) -> Utilisateur:
    utilisateur = db.get(Utilisateur, utilisateur_id)
    if utilisateur is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    return utilisateur


@router.post("", response_model=UtilisateurOut, status_code=status.HTTP_201_CREATED)
def creer_utilisateur(
    payload: UtilisateurCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    if db.query(Utilisateur).filter(Utilisateur.telephone == payload.telephone).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce numero de telephone est deja utilise")
    if payload.email and db.query(Utilisateur).filter(func.lower(Utilisateur.email) == payload.email.lower()).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cet email est deja utilise")

    utilisateur = Utilisateur(
        entreprise_id=payload.entreprise_id,
        role=payload.role,
        nom=payload.nom,
        telephone=payload.telephone,
        email=payload.email,
        mot_de_passe_hash=hash_password(payload.mot_de_passe),
    )
    db.add(utilisateur)
    db.flush()
    enregistrer_audit(
        db,
        entite_type="Utilisateur",
        entite_id=utilisateur.id,
        action="creation",
        utilisateur_id=current_user.id,
        valeur_apres={"telephone": utilisateur.telephone, "role": utilisateur.role.value},
    )
    db.commit()
    db.refresh(utilisateur)
    return utilisateur


@router.get("", response_model=list[UtilisateurOut])
def lister_utilisateurs(
    response: Response,
    entreprise_id: uuid.UUID | None = None,
    role: RoleUtilisateur | None = None,
    page: int | None = None,
    per_page: int | None = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    """Un admin peut lister les utilisateurs de n'importe quelle entreprise (ou sans
    filtre). Tout autre role ne voit jamais que les collegues de sa propre entreprise :
    entreprise_id est alors force a la sienne, quelle que soit la valeur fournie."""
    query = db.query(Utilisateur)
    if current_user.role == RoleUtilisateur.ADMIN:
        if entreprise_id is not None:
            query = query.filter(Utilisateur.entreprise_id == entreprise_id)
    else:
        query = query.filter(Utilisateur.entreprise_id == current_user.entreprise_id)
    if role is not None:
        query = query.filter(Utilisateur.role == role)

    query = query.order_by(Utilisateur.date_creation.desc())

    if page is not None or per_page is not None:
        page = page or 1
        per_page = per_page or 25
        response.headers["X-Total-Count"] = str(query.count())
        query = query.offset((page - 1) * per_page).limit(per_page)

    return query.all()


@router.get("/{utilisateur_id}", response_model=UtilisateurOut)
def obtenir_utilisateur(
    utilisateur_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    return _get_utilisateur_or_404(db, utilisateur_id)


@router.put("/{utilisateur_id}", response_model=UtilisateurOut)
def modifier_utilisateur(
    utilisateur_id: uuid.UUID,
    payload: UtilisateurUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    utilisateur = _get_utilisateur_or_404(db, utilisateur_id)
    if payload.email and payload.email.lower() != (utilisateur.email or "").lower():
        if db.query(Utilisateur).filter(
            Utilisateur.id != utilisateur_id, func.lower(Utilisateur.email) == payload.email.lower()
        ).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cet email est deja utilise")

    avant = {"role": utilisateur.role.value, "compte_actif": utilisateur.compte_actif}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(utilisateur, field, value)

    enregistrer_audit(
        db,
        entite_type="Utilisateur",
        entite_id=utilisateur.id,
        action="modification",
        utilisateur_id=current_user.id,
        valeur_avant=avant,
        valeur_apres=payload.model_dump(exclude_unset=True, mode="json"),
    )
    db.commit()
    db.refresh(utilisateur)
    return utilisateur


@router.delete("/{utilisateur_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_utilisateur(
    utilisateur_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    utilisateur = _get_utilisateur_or_404(db, utilisateur_id)

    a_des_actions_auditees = (
        db.query(JournalAudit)
        .filter(JournalAudit.entite_type == "Utilisateur", JournalAudit.entite_id == utilisateur.id)
        .first()
        is not None
    )
    if a_des_actions_auditees:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cet utilisateur a deja des actions dans le journal d'audit et ne peut pas etre "
                "supprime physiquement ; desactivez son compte (compte_actif=false) a la place"
            ),
        )

    db.delete(utilisateur)
    enregistrer_audit(
        db,
        entite_type="Utilisateur",
        entite_id=utilisateur.id,
        action="suppression",
        utilisateur_id=current_user.id,
        valeur_apres={"telephone": utilisateur.telephone},
    )
    db.commit()
