import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.enums import ActionLitige, RoleUtilisateur, StatutFacture, StatutLitige
from app.models.facture import Facture
from app.models.litige_dossier import LitigeDossier
from app.models.utilisateur import Utilisateur
from app.schemas.litige import LitigeActionRequest, LitigeCreate, LitigeOut
from app.services.audit import enregistrer_audit

router = APIRouter(prefix="/litiges", tags=["litiges"])

_ROLES_ADMIN = [RoleUtilisateur.ADMIN]


def _vers_out(dossier: LitigeDossier) -> LitigeOut:
    facture = dossier.facture
    partenaire_concerne = facture.avance.partenaire_financier.raison_sociale if facture.avance else None
    return LitigeOut(
        id=dossier.id,
        facture_id=facture.id,
        numero_facture=facture.numero_facture,
        fournisseur=facture.pme.raison_sociale,
        acheteur=facture.donneur_ordre.raison_sociale,
        partenaire_concerne=partenaire_concerne,
        cause=dossier.cause,
        montant_en_jeu=dossier.montant_en_jeu,
        description=dossier.description,
        statut=dossier.statut,
        derniere_action=dossier.derniere_action,
        resolution_note=dossier.resolution_note,
        ouvert_le=dossier.ouvert_le,
        resolu_le=dossier.resolu_le,
    )


@router.post(
    "",
    response_model=LitigeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Ouvre un dossier de litige sur une facture (admin uniquement)",
    description=(
        "Le passage en litige reste une action manuelle au MVP (aucune automatisation, voir "
        "architecture-mvp-affacturage-inverse.md §5.5) : c'est l'admin qui instruit chaque cas. "
        "Le statut courant de la facture est conserve pour etre restaure telle quelle a la "
        "resolution du dossier."
    ),
)
def ouvrir_litige(
    payload: LitigeCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    facture = db.get(Facture, payload.facture_id)
    if facture is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facture introuvable")
    if facture.statut == StatutFacture.LITIGE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette facture est deja en litige")

    dossier = LitigeDossier(
        facture_id=facture.id,
        cause=payload.cause,
        montant_en_jeu=payload.montant_en_jeu,
        description=payload.description,
        statut_facture_avant=facture.statut,
        ouvert_par_id=current_user.id,
    )
    facture.statut = StatutFacture.LITIGE
    db.add(dossier)
    db.flush()

    enregistrer_audit(
        db,
        entite_type="LitigeDossier",
        entite_id=dossier.id,
        action="ouverture",
        utilisateur_id=current_user.id,
        valeur_apres={"facture_id": str(facture.id), "cause": dossier.cause.value},
    )
    db.commit()
    db.refresh(dossier)
    return _vers_out(dossier)


@router.get(
    "",
    response_model=list[LitigeOut],
    summary="Liste les dossiers de litige (admin uniquement)",
)
def lister_litiges(
    statut: StatutLitige | None = None,
    cause: str | None = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    query = db.query(LitigeDossier)
    if statut is not None:
        query = query.filter(LitigeDossier.statut == statut)
    if cause is not None:
        query = query.filter(LitigeDossier.cause == cause)
    dossiers = query.order_by(LitigeDossier.ouvert_le.desc()).all()
    return [_vers_out(d) for d in dossiers]


@router.get(
    "/{litige_id}",
    response_model=LitigeOut,
    summary="Consulte un dossier de litige (admin uniquement)",
)
def obtenir_litige(
    litige_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    dossier = db.get(LitigeDossier, litige_id)
    if dossier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier de litige introuvable")
    return _vers_out(dossier)


@router.patch(
    "/{litige_id}",
    response_model=LitigeOut,
    summary="Enregistre une action sur un dossier de litige (admin uniquement)",
    description=(
        "`contacter_parties`/`engager_recouvrement`/`proposer_resolution` ne font qu'enregistrer "
        "la derniere action prise (pas d'integration email/SMS reelle au MVP). "
        "`marquer_resolu` cloture le dossier et restaure sur la facture le statut qu'elle avait "
        "juste avant l'ouverture du litige."
    ),
)
def agir_sur_litige(
    litige_id: uuid.UUID,
    payload: LitigeActionRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    dossier = db.get(LitigeDossier, litige_id)
    if dossier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier de litige introuvable")
    if dossier.statut == StatutLitige.RESOLU:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce dossier est deja resolu")

    avant = {"statut": dossier.statut.value, "derniere_action": dossier.derniere_action}
    dossier.derniere_action = payload.action.value

    if payload.action == ActionLitige.MARQUER_RESOLU:
        dossier.statut = StatutLitige.RESOLU
        dossier.resolution_note = payload.resolution_note
        dossier.resolu_le = datetime.now(timezone.utc)
        dossier.facture.statut = dossier.statut_facture_avant
    else:
        dossier.statut = StatutLitige.EN_COURS
        if payload.resolution_note:
            dossier.resolution_note = payload.resolution_note

    enregistrer_audit(
        db,
        entite_type="LitigeDossier",
        entite_id=dossier.id,
        action=f"action_{payload.action.value}",
        utilisateur_id=current_user.id,
        valeur_avant=avant,
        valeur_apres={"statut": dossier.statut.value, "derniere_action": dossier.derniere_action},
    )
    db.commit()
    db.refresh(dossier)
    return _vers_out(dossier)
