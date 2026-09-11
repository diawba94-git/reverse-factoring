import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.avance import Avance
from app.models.convention_domiciliation import ConventionDomiciliation
from app.models.enums import RoleUtilisateur, StatutCompteDedie, StatutRelation
from app.models.facture import Facture
from app.models.relation_pme_donneur_ordre import RelationPmeDonneurOrdre, ValidateurRelation
from app.models.utilisateur import Utilisateur
from app.schemas.relation import (
    ConventionSignatureUpdate,
    RelationChipOut,
    RelationOut,
    RelationResumeOut,
    RelationStatutUpdate,
    ValidateurAvecRelationsOut,
)
from app.services.audit import enregistrer_audit
from app.services.roles import ROLES_VALIDATEURS

router = APIRouter(prefix="/relations", tags=["relations"])

_ROLES_SUPERVISION = [RoleUtilisateur.ADMIN, RoleUtilisateur.AGENT_FINANCIER]
_ROLES_LECTURE = [RoleUtilisateur.ADMIN, RoleUtilisateur.AGENT_FINANCIER, RoleUtilisateur.VALIDATEUR_1, RoleUtilisateur.VALIDATEUR_2]


def _vers_out(relation: RelationPmeDonneurOrdre, db: Session) -> RelationOut:
    convention = (
        db.query(ConventionDomiciliation).filter(ConventionDomiciliation.relation_id == relation.id).first()
    )
    nombre_signatures = 0
    compte_statut = None
    if convention is not None:
        nombre_signatures = sum(
            [convention.signature_pme, convention.signature_donneur_ordre, convention.signature_partenaire]
        )
        if convention.compte_dedie is not None:
            compte_statut = convention.compte_dedie.statut
    return RelationOut(
        id=relation.id,
        pme_id=relation.pme_id,
        pme_raison_sociale=relation.pme.raison_sociale,
        donneur_ordre_id=relation.donneur_ordre_id,
        donneur_ordre_raison_sociale=relation.donneur_ordre.raison_sociale,
        statut=relation.statut,
        factures_pilote_max=relation.factures_pilote_max,
        factures_pilote_utilisees=relation.factures_pilote_utilisees,
        date_debut_relation=relation.date_debut_relation,
        compte_dedie_statut=compte_statut,
        nombre_signatures=nombre_signatures,
    )


@router.get(
    "/resume",
    response_model=RelationResumeOut,
    summary="Compte les relations PME<->donneur d'ordre par statut (admin/partenaire)",
)
def resume_relations(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_SUPERVISION)),
):
    pilote = db.query(RelationPmeDonneurOrdre).filter(RelationPmeDonneurOrdre.statut == StatutRelation.PILOTE).count()
    signee = (
        db.query(RelationPmeDonneurOrdre)
        .filter(RelationPmeDonneurOrdre.statut == StatutRelation.CONVENTION_SIGNEE)
        .count()
    )
    return RelationResumeOut(pilote=pilote, convention_signee=signee)


@router.get(
    "",
    response_model=list[RelationOut],
    summary="Liste les relations PME<->donneur d'ordre (admin/partenaire, ou validateur scope a sa propre entreprise)",
)
def lister_relations(
    pme_id: uuid.UUID | None = None,
    donneur_ordre_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_LECTURE)),
):
    query = db.query(RelationPmeDonneurOrdre)
    if current_user.role in ROLES_VALIDATEURS:
        # Jamais deduit d'un donneur_ordre_id fourni par le client pour ce role : toujours
        # sa propre entreprise (meme convention que lister_factures/lister_avances).
        query = query.filter(RelationPmeDonneurOrdre.donneur_ordre_id == current_user.entreprise_id)
    elif current_user.role == RoleUtilisateur.AGENT_FINANCIER:
        # Portefeuille du partenaire : les couples (pme, donneur d'ordre) pour lesquels il
        # a finance au moins une avance, jamais toutes les relations de la plateforme.
        paires = (
            db.query(Facture.pme_id, Facture.donneur_ordre_id)
            .join(Avance, Avance.facture_id == Facture.id)
            .filter(Avance.partenaire_financier_id == current_user.entreprise_id)
            .distinct()
            .all()
        )
        if not paires:
            return []
        query = query.filter(
            or_(
                *[
                    and_(RelationPmeDonneurOrdre.pme_id == p, RelationPmeDonneurOrdre.donneur_ordre_id == d)
                    for p, d in paires
                ]
            )
        )
    else:
        if donneur_ordre_id is not None:
            query = query.filter(RelationPmeDonneurOrdre.donneur_ordre_id == donneur_ordre_id)
    if pme_id is not None:
        query = query.filter(RelationPmeDonneurOrdre.pme_id == pme_id)
    return [_vers_out(r, db) for r in query.order_by(RelationPmeDonneurOrdre.date_debut_relation.desc()).all()]


@router.get(
    "/validateurs",
    response_model=list[ValidateurAvecRelationsOut],
    summary="Liste les validateurs de l'entreprise de l'appelant avec leurs relations PME affectees",
)
def lister_validateurs_avec_relations(
    current_user: Utilisateur = Depends(require_role([RoleUtilisateur.VALIDATEUR_1, RoleUtilisateur.VALIDATEUR_2, RoleUtilisateur.ADMIN])),
    db: Session = Depends(get_db),
):
    entreprise_id = current_user.entreprise_id
    validateurs = (
        db.query(Utilisateur)
        .filter(
            Utilisateur.entreprise_id == entreprise_id,
            Utilisateur.role.in_([RoleUtilisateur.VALIDATEUR_1, RoleUtilisateur.VALIDATEUR_2]),
        )
        .order_by(Utilisateur.date_creation.asc())
        .all()
    )

    relations = db.query(RelationPmeDonneurOrdre).filter(RelationPmeDonneurOrdre.donneur_ordre_id == entreprise_id).all()
    affectations = (
        db.query(ValidateurRelation)
        .join(RelationPmeDonneurOrdre, RelationPmeDonneurOrdre.id == ValidateurRelation.relation_id)
        .filter(RelationPmeDonneurOrdre.donneur_ordre_id == entreprise_id)
        .all()
    )

    relation_par_id = {r.id: r for r in relations}
    utilisateurs_par_relation: dict[uuid.UUID, set[uuid.UUID]] = {}
    for a in affectations:
        utilisateurs_par_relation.setdefault(a.relation_id, set()).add(a.utilisateur_id)

    def chip(relation: RelationPmeDonneurOrdre) -> RelationChipOut:
        return RelationChipOut(relation_id=relation.id, pme_id=relation.pme_id, pme_raison_sociale=relation.pme.raison_sociale)

    relations_sans_validateur_2 = [
        relation_par_id[rid]
        for rid, users in utilisateurs_par_relation.items()
        if rid in relation_par_id
        and any(u.id in users and u.role == RoleUtilisateur.VALIDATEUR_1 for u in validateurs)
        and not any(u.id in users and u.role == RoleUtilisateur.VALIDATEUR_2 for u in validateurs)
    ]

    resultat = []
    for u in validateurs:
        mes_relations = [
            chip(relation_par_id[rid])
            for rid, users in utilisateurs_par_relation.items()
            if u.id in users and rid in relation_par_id
        ]
        en_attente = [chip(r) for r in relations_sans_validateur_2] if u.role == RoleUtilisateur.VALIDATEUR_2 else []
        resultat.append(
            ValidateurAvecRelationsOut(
                utilisateur_id=u.id,
                nom=u.nom,
                role=u.role.value,
                relations=mes_relations,
                relations_en_attente=en_attente,
            )
        )
    return resultat


@router.patch(
    "/{relation_id}",
    response_model=RelationOut,
    summary="Fait passer une relation de pilote a convention_signee, ou inversement (admin uniquement)",
    description=(
        "Le passage de pilote a convention_signee reste une decision manuelle (doc §5.5) — "
        "jamais une bascule automatique au dernier credit du quota pilote."
    ),
)
def modifier_statut_relation(
    relation_id: uuid.UUID,
    payload: RelationStatutUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role([RoleUtilisateur.ADMIN])),
):
    relation = db.get(RelationPmeDonneurOrdre, relation_id)
    if relation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relation introuvable")

    avant = {"statut": relation.statut.value}
    relation.statut = payload.statut
    enregistrer_audit(
        db,
        entite_type="RelationPmeDonneurOrdre",
        entite_id=relation.id,
        action="maj_statut",
        utilisateur_id=current_user.id,
        valeur_avant=avant,
        valeur_apres={"statut": relation.statut.value},
    )
    db.commit()
    db.refresh(relation)
    return _vers_out(relation, db)


@router.patch(
    "/{relation_id}/convention",
    response_model=RelationOut,
    summary="Coche une signature de la convention de domiciliation (admin uniquement)",
    description=(
        "Cycle de vie manuel (doc §3.3ter) : pas de signature electronique reelle. Quand les "
        "3 parties ont signe, le compte dedie passe actif et la relation convention_signee."
    ),
)
def signer_convention(
    relation_id: uuid.UUID,
    payload: ConventionSignatureUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role([RoleUtilisateur.ADMIN])),
):
    relation = db.get(RelationPmeDonneurOrdre, relation_id)
    if relation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relation introuvable")
    convention = db.query(ConventionDomiciliation).filter(ConventionDomiciliation.relation_id == relation_id).first()
    if convention is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Convention introuvable pour cette relation")

    if payload.signature_pme is not None:
        convention.signature_pme = payload.signature_pme
    if payload.signature_donneur_ordre is not None:
        convention.signature_donneur_ordre = payload.signature_donneur_ordre
    if payload.signature_partenaire is not None:
        convention.signature_partenaire = payload.signature_partenaire

    if convention.signature_pme and convention.signature_donneur_ordre and convention.signature_partenaire:
        if convention.compte_dedie is not None:
            convention.compte_dedie.statut = StatutCompteDedie.ACTIF
        relation.statut = StatutRelation.CONVENTION_SIGNEE

    enregistrer_audit(
        db,
        entite_type="ConventionDomiciliation",
        entite_id=convention.id,
        action="maj_signature",
        utilisateur_id=current_user.id,
        valeur_apres={
            "signature_pme": convention.signature_pme,
            "signature_donneur_ordre": convention.signature_donneur_ordre,
            "signature_partenaire": convention.signature_partenaire,
        },
    )
    db.commit()
    db.refresh(relation)
    return _vers_out(relation, db)
