import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.avance import Avance
from app.models.avoir_facture import AvoirFacture
from app.models.creance_compensation import CreanceCompensation
from app.models.enums import RoleUtilisateur, StatutAvoir
from app.models.facture import Facture
from app.models.utilisateur import Utilisateur
from app.schemas.avoir import AvoirCreate, AvoirOut, CreanceOut
from app.services.audit import enregistrer_audit
from app.services.gestion_avoirs import annuler_effet_avoir, appliquer_avoir, get_creances_actives
from app.services.numerotation_avoir import generer_prochain_numero
from app.services.roles import ROLES_VALIDATEURS

router = APIRouter(tags=["avoirs"])


def _get_facture_or_404(db: Session, facture_id: uuid.UUID) -> Facture:
    facture = db.get(Facture, facture_id)
    if facture is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facture introuvable")
    return facture


def _get_avoir_or_404(db: Session, avoir_id: uuid.UUID) -> AvoirFacture:
    avoir = db.get(AvoirFacture, avoir_id)
    if avoir is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avoir introuvable")
    return avoir


@router.post("/factures/{facture_id}/avoirs", response_model=AvoirOut, status_code=status.HTTP_201_CREATED)
def creer_avoir(
    facture_id: uuid.UUID,
    payload: AvoirCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role([RoleUtilisateur.MEMBRE_PME])),
):
    facture = _get_facture_or_404(db, facture_id)
    if facture.pme_id != current_user.entreprise_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette facture ne vous appartient pas")

    # Le montant restant du de la facture tient compte des avoirs deja confirmes (deja
    # deduits de facture.montant_ttc au moment de leur confirmation, voir
    # app.services.gestion_avoirs) et des avoirs encore en attente sur cette meme facture
    # (pas encore deduits, mais deja "engages") — jamais des avoirs rejetes, sans effet.
    montant_deja_engage = sum(
        (a.montant_ttc for a in facture.avoirs if a.statut == StatutAvoir.EMIS),
        Decimal("0"),
    )
    montant_restant_du = facture.montant_ttc - montant_deja_engage
    if payload.montant_ttc > montant_restant_du:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Le montant de l'avoir ({payload.montant_ttc}) depasse le montant restant du "
                f"de cette facture ({montant_restant_du})."
            ),
        )

    avoir = AvoirFacture(
        numero_avoir=generer_prochain_numero(db, facture.pme_id, date.today().year),
        facture_id=facture.id,
        montant_ht=payload.montant_ht,
        montant_tva=payload.montant_tva,
        montant_ttc=payload.montant_ttc,
        motif=payload.motif,
        statut=StatutAvoir.EMIS,
        date_emission=date.today(),
        piece_justificative_url=payload.piece_justificative_url,
    )
    db.add(avoir)
    db.flush()

    enregistrer_audit(
        db,
        entite_type="AvoirFacture",
        entite_id=avoir.id,
        action="creation",
        utilisateur_id=current_user.id,
        valeur_apres={"facture_id": str(facture.id), "montant_ttc": str(avoir.montant_ttc), "motif": avoir.motif.value},
    )
    db.commit()
    db.refresh(avoir)
    return avoir


@router.post("/avoirs/{avoir_id}/confirmer", response_model=AvoirOut)
def confirmer_avoir(
    avoir_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(list(ROLES_VALIDATEURS))),
):
    avoir = _get_avoir_or_404(db, avoir_id)
    facture = avoir.facture
    if facture.donneur_ordre_id != current_user.entreprise_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez confirmer que les avoirs sur des factures adressees a votre entreprise",
        )
    if avoir.statut != StatutAvoir.EMIS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossible de confirmer un avoir au statut '{avoir.statut.value}'",
        )

    avant = {"statut": avoir.statut.value}
    resultat = appliquer_avoir(db, avoir, facture, facture.avance)
    avoir.statut = StatutAvoir.CONFIRME_PAR_ACHETEUR

    enregistrer_audit(
        db,
        entite_type="AvoirFacture",
        entite_id=avoir.id,
        action="confirmation",
        utilisateur_id=current_user.id,
        valeur_avant=avant,
        valeur_apres={"statut": avoir.statut.value, "effet": resultat["effet"]},
    )
    db.commit()
    db.refresh(avoir)
    return avoir


@router.post("/avoirs/{avoir_id}/rejeter", response_model=AvoirOut)
def rejeter_avoir(
    avoir_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(list(ROLES_VALIDATEURS))),
):
    avoir = _get_avoir_or_404(db, avoir_id)
    facture = avoir.facture
    if facture.donneur_ordre_id != current_user.entreprise_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez rejeter que les avoirs sur des factures adressees a votre entreprise",
        )
    if avoir.statut == StatutAvoir.REJETE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cet avoir a deja ete rejete")

    avant = {"statut": avoir.statut.value}
    annuler_effet_avoir(db, avoir, facture, facture.avance)
    avoir.statut = StatutAvoir.REJETE

    enregistrer_audit(
        db,
        entite_type="AvoirFacture",
        entite_id=avoir.id,
        action="rejet",
        utilisateur_id=current_user.id,
        valeur_avant=avant,
        valeur_apres={"statut": avoir.statut.value},
    )
    db.commit()
    db.refresh(avoir)
    return avoir


@router.get("/avoirs", response_model=list[AvoirOut])
def lister_avoirs(
    response: Response,
    pme_id: uuid.UUID | None = None,
    donneur_ordre_id: uuid.UUID | None = None,
    statut: StatutAvoir | None = None,
    date_debut: date | None = None,
    date_fin: date | None = None,
    page: int | None = None,
    per_page: int | None = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    query = db.query(AvoirFacture).join(Facture, Facture.id == AvoirFacture.facture_id)

    if current_user.role == RoleUtilisateur.MEMBRE_PME:
        query = query.filter(Facture.pme_id == current_user.entreprise_id)
    elif current_user.role in ROLES_VALIDATEURS:
        query = query.filter(Facture.donneur_ordre_id == current_user.entreprise_id)
    elif current_user.role == RoleUtilisateur.AGENT_FINANCIER:
        # Lecture seule : les avoirs qui impactent un financement de ce partenaire (voir
        # ecran "Avoirs sur mon portefeuille") — jamais ceux d'une facture pas encore
        # avancee, qui ne le concernent pas encore.
        query = query.join(Avance, Avance.facture_id == Facture.id).filter(
            Avance.partenaire_financier_id == current_user.entreprise_id
        )
    elif current_user.role == RoleUtilisateur.ADMIN:
        if pme_id is not None:
            query = query.filter(Facture.pme_id == pme_id)
        if donneur_ordre_id is not None:
            query = query.filter(Facture.donneur_ordre_id == donneur_ordre_id)
    else:
        return []

    if statut is not None:
        query = query.filter(AvoirFacture.statut == statut)
    if date_debut is not None:
        query = query.filter(AvoirFacture.date_emission >= date_debut)
    if date_fin is not None:
        query = query.filter(AvoirFacture.date_emission <= date_fin)

    query = query.order_by(AvoirFacture.created_at.desc())

    if page is not None or per_page is not None:
        page = page or 1
        per_page = per_page or 25
        response.headers["X-Total-Count"] = str(query.count())
        query = query.offset((page - 1) * per_page).limit(per_page)

    return query.all()


@router.get("/pme/{pme_id}/creances", response_model=list[CreanceOut])
def lister_creances_pme(
    pme_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    if current_user.role == RoleUtilisateur.MEMBRE_PME and current_user.entreprise_id != pme_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse a ces creances")
    if current_user.role not in (RoleUtilisateur.MEMBRE_PME, RoleUtilisateur.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse a ces creances")

    return get_creances_actives(db, pme_id)


@router.get(
    "/creances",
    response_model=list[CreanceOut],
    summary="Supervision globale des creances de compensation (admin), toutes PME confondues",
)
def lister_toutes_creances(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role([RoleUtilisateur.ADMIN])),
):
    return db.query(CreanceCompensation).order_by(CreanceCompensation.date_creation.desc()).all()
