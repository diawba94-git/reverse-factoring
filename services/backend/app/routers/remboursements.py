import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.avance import Avance
from app.models.enums import RoleUtilisateur, StatutAvance, StatutFacture, StatutRapprochement
from app.models.remboursement import Remboursement
from app.models.utilisateur import Utilisateur
from app.schemas.remboursement import RapprochementRequest, RemboursementCreate, RemboursementOut
from app.services.audit import enregistrer_audit

router = APIRouter(prefix="/remboursements", tags=["remboursements"])

_ROLES_AUTORISES = [RoleUtilisateur.AGENT_FINANCIER, RoleUtilisateur.ADMIN]
_TOLERANCE = Decimal("0.01")


def _get_remboursement_or_404(db: Session, remboursement_id: uuid.UUID) -> Remboursement:
    remboursement = db.get(Remboursement, remboursement_id)
    if remboursement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remboursement introuvable")
    return remboursement


@router.post("", response_model=RemboursementOut, status_code=status.HTTP_201_CREATED)
def enregistrer_remboursement(
    payload: RemboursementCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_AUTORISES)),
):
    avance = db.get(Avance, payload.avance_id)
    if avance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avance introuvable")
    if avance.statut != StatutAvance.AVANCE_VERSEE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossible d'enregistrer un remboursement pour une avance au statut '{avance.statut.value}'",
        )

    remboursement = Remboursement(
        avance_id=payload.avance_id,
        montant_recu=payload.montant_recu,
        date_reception=payload.date_reception,
        source_entreprise_id=payload.source_entreprise_id,
        statut_rapprochement=StatutRapprochement.EN_ATTENTE,
    )
    db.add(remboursement)
    db.flush()
    enregistrer_audit(
        db,
        entite_type="Remboursement",
        entite_id=remboursement.id,
        action="creation",
        utilisateur_id=current_user.id,
        valeur_apres={"avance_id": str(avance.id), "montant_recu": str(remboursement.montant_recu)},
    )
    db.commit()
    db.refresh(remboursement)
    return remboursement


@router.post("/{remboursement_id}/rapprocher", response_model=RemboursementOut)
def rapprocher_remboursement(
    remboursement_id: uuid.UUID,
    payload: RapprochementRequest | None = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_AUTORISES)),
):
    remboursement = _get_remboursement_or_404(db, remboursement_id)
    avance = remboursement.avance

    avant = {"statut_rapprochement": remboursement.statut_rapprochement.value}

    if payload is not None:
        nouveau_statut = payload.statut_rapprochement
    else:
        ecart = abs(remboursement.montant_recu - avance.montant_solde_du)
        nouveau_statut = StatutRapprochement.RAPPROCHE if ecart <= _TOLERANCE else StatutRapprochement.ECART_DETECTE

    remboursement.statut_rapprochement = nouveau_statut

    if nouveau_statut == StatutRapprochement.RAPPROCHE:
        remboursement.declenche_versement_solde = True
        avance.statut = StatutAvance.SOLDEE
        avance.date_versement_solde = datetime.now(timezone.utc)
        avance.facture.statut = StatutFacture.SOLDEE

    enregistrer_audit(
        db,
        entite_type="Remboursement",
        entite_id=remboursement.id,
        action="rapprochement",
        utilisateur_id=current_user.id,
        valeur_avant=avant,
        valeur_apres={"statut_rapprochement": remboursement.statut_rapprochement.value},
    )
    db.commit()
    db.refresh(remboursement)
    return remboursement
