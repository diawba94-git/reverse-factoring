import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.article_faq import ArticleFaq
from app.models.enums import RoleUtilisateur
from app.models.utilisateur import Utilisateur
from app.schemas.article_faq import ArticleFaqCreate, ArticleFaqOut, ArticleFaqUpdate
from app.services.audit import enregistrer_audit

router = APIRouter(prefix="/faq", tags=["faq"])

_ROLES_ADMIN = [RoleUtilisateur.ADMIN]


def _get_article_or_404(db: Session, article_id: uuid.UUID) -> ArticleFaq:
    article = db.get(ArticleFaq, article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article introuvable")
    return article


@router.get("", response_model=list[ArticleFaqOut])
def lister_articles(
    portee: str | None = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    query = db.query(ArticleFaq)
    if portee is not None:
        query = query.filter(ArticleFaq.portee == portee)
    return query.order_by(ArticleFaq.created_at.desc()).all()


@router.post("", response_model=ArticleFaqOut, status_code=status.HTTP_201_CREATED)
def creer_article(
    payload: ArticleFaqCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    article = ArticleFaq(**payload.model_dump())
    db.add(article)
    db.flush()
    enregistrer_audit(
        db,
        entite_type="ArticleFaq",
        entite_id=article.id,
        action="creation",
        utilisateur_id=current_user.id,
        valeur_apres={"question": article.question, "portee": article.portee},
    )
    db.commit()
    db.refresh(article)
    return article


@router.put("/{article_id}", response_model=ArticleFaqOut)
def modifier_article(
    article_id: uuid.UUID,
    payload: ArticleFaqUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    article = _get_article_or_404(db, article_id)
    avant = {"question": article.question, "publie": article.publie}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(article, field, value)

    enregistrer_audit(
        db,
        entite_type="ArticleFaq",
        entite_id=article.id,
        action="modification",
        utilisateur_id=current_user.id,
        valeur_avant=avant,
        valeur_apres=payload.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(article)
    return article


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_article(
    article_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    article = _get_article_or_404(db, article_id)
    db.delete(article)
    enregistrer_audit(
        db,
        entite_type="ArticleFaq",
        entite_id=article.id,
        action="suppression",
        utilisateur_id=current_user.id,
        valeur_apres={"question": article.question},
    )
    db.commit()
