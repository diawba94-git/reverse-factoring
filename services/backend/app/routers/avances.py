import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.avance import Avance
from app.models.entreprise import Entreprise
from app.models.enums import RoleUtilisateur, StatutAvance, StatutChequeGarantie, StatutFacture, TypeEntreprise, TypeLimite
from app.models.facture import Facture
from app.models.limite_credit import LimiteCredit
from app.models.enveloppe_partenaire import EnveloppePartenaire
from app.models.utilisateur import Utilisateur
from app.models.remboursement import Remboursement
from app.models.relation_pme_donneur_ordre import RelationPmeDonneurOrdre
from app.schemas.avance import AvanceCreate, AvanceOut, AvanceRejetRequest, ChequeResumeOut, DossierDecisionOut
from app.services.audit import enregistrer_audit
from app.services.gestion_avoirs import verifier_et_deduire_creances
from app.services.roles import ROLES_VALIDATEURS
from app.services.calcul_frais import DureeInsuffisanteError, TaegDepasseError, calculer_frais
from app.services.grille import obtenir_grille_active

router = APIRouter(prefix="/avances", tags=["avances"])


def _get_avance_or_404(db: Session, avance_id: uuid.UUID) -> Avance:
    avance = db.get(Avance, avance_id)
    if avance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avance introuvable")
    return avance


@router.post("", response_model=AvanceOut, status_code=status.HTTP_201_CREATED)
def demander_avance(
    payload: AvanceCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role([RoleUtilisateur.MEMBRE_PME, RoleUtilisateur.ADMIN])),
):
    facture = db.get(Facture, payload.facture_id)
    if facture is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facture introuvable")
    if current_user.role != RoleUtilisateur.ADMIN and facture.pme_id != current_user.entreprise_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette facture ne vous appartient pas")
    if facture.statut != StatutFacture.VALIDEE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La facture doit etre au statut 'validee' pour demander une avance (statut actuel : '{facture.statut.value}')",
        )
    if db.query(Avance).filter(Avance.facture_id == facture.id).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Une avance existe deja pour cette facture")

    partenaire = db.get(Entreprise, payload.partenaire_financier_id)
    if partenaire is None or partenaire.type != TypeEntreprise.PARTENAIRE_FINANCIER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le partenaire financier indique est introuvable ou n'est pas de type PARTENAIRE_FINANCIER",
        )

    grille = obtenir_grille_active(db)
    try:
        resultat = calculer_frais(facture.montant_ttc, facture.duree_jours, grille)
    except DureeInsuffisanteError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TaegDepasseError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    garantie_detenue = facture.cheque_garantie is not None and facture.cheque_garantie.statut in (
        StatutChequeGarantie.CONFIRME_PAR_DONNEUR_ORDRE,
        StatutChequeGarantie.REMIS_AU_PARTENAIRE,
    )

    # Doc §3.0sexies : une creance de compensation en attente (reliquat d'un avoir qui
    # depassait le solde d'une precedente avance) est toujours prioritaire, quelle que soit
    # la facture ou le donneur d'ordre concerne par cette nouvelle avance — deduite ici du
    # montant qui sera effectivement verse a la PME, jamais des frais/parts calcules.
    montant_avance_a_verser = verifier_et_deduire_creances(db, facture.pme_id, resultat.montant_avance_initial)

    avance = Avance(
        facture_id=facture.id,
        partenaire_financier_id=partenaire.id,
        grille_tarifaire_id=grille.id,
        montant_avance_initial=montant_avance_a_verser,
        frais_total=resultat.frais_total,
        montant_solde_du=resultat.montant_solde_du,
        part_partenaire=resultat.part_partenaire,
        part_plateforme=resultat.part_plateforme,
        taeg_annualise=resultat.taeg_annualise,
        methode_versement=payload.methode_versement,
        statut=StatutAvance.EN_ATTENTE_VALIDATION,
        garantie_detenue_avant_financement=garantie_detenue,
    )
    db.add(avance)

    facture.statut = StatutFacture.AVANCE_DEMANDEE

    db.flush()
    enregistrer_audit(
        db,
        entite_type="Avance",
        entite_id=avance.id,
        action="creation",
        utilisateur_id=current_user.id,
        valeur_apres={"facture_id": str(facture.id), "montant_avance_initial": str(avance.montant_avance_initial)},
    )
    db.commit()
    db.refresh(avance)
    return avance


@router.get("", response_model=list[AvanceOut])
def lister_avances(
    response: Response,
    statut: StatutAvance | None = None,
    partenaire_financier_id: uuid.UUID | None = None,
    pme_id: uuid.UUID | None = None,
    tri: str | None = None,
    page: int | None = None,
    per_page: int | None = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    query = db.query(Avance)
    facture_jointe = False

    if current_user.role == RoleUtilisateur.MEMBRE_PME:
        query = query.join(Facture, Facture.id == Avance.facture_id).filter(
            Facture.pme_id == current_user.entreprise_id
        )
        facture_jointe = True
    elif current_user.role == RoleUtilisateur.AGENT_FINANCIER:
        query = query.filter(Avance.partenaire_financier_id == current_user.entreprise_id)
    elif current_user.role in ROLES_VALIDATEURS:
        query = query.join(Facture, Facture.id == Avance.facture_id).filter(
            Facture.donneur_ordre_id == current_user.entreprise_id
        )
        facture_jointe = True
    elif current_user.role == RoleUtilisateur.ADMIN and pme_id is not None:
        query = query.join(Facture, Facture.id == Avance.facture_id).filter(Facture.pme_id == pme_id)
        facture_jointe = True

    if statut is not None:
        query = query.filter(Avance.statut == statut)
    if partenaire_financier_id is not None:
        query = query.filter(Avance.partenaire_financier_id == partenaire_financier_id)

    if tri == "echeance_asc":
        if not facture_jointe:
            query = query.join(Facture, Facture.id == Avance.facture_id)
        query = query.order_by(Facture.date_echeance.asc())
    else:
        query = query.order_by(Avance.created_at.desc())

    if page is not None or per_page is not None:
        page = page or 1
        per_page = per_page or 25
        response.headers["X-Total-Count"] = str(query.count())
        query = query.offset((page - 1) * per_page).limit(per_page)

    return query.all()


@router.get("/{avance_id}", response_model=AvanceOut)
def obtenir_avance(
    avance_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    return _get_avance_or_404(db, avance_id)


@router.get(
    "/{avance_id}/dossier-decision",
    response_model=DossierDecisionOut,
    summary="Vue consolidee pour la decision du partenaire (agent_financier proprietaire ou admin)",
)
def dossier_decision(
    avance_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role([RoleUtilisateur.AGENT_FINANCIER, RoleUtilisateur.ADMIN])),
):
    avance = _get_avance_or_404(db, avance_id)
    if current_user.role != RoleUtilisateur.ADMIN and avance.partenaire_financier_id != current_user.entreprise_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette avance ne vous appartient pas")

    facture = avance.facture
    pme = facture.pme
    donneur_ordre = facture.donneur_ordre

    relation = (
        db.query(RelationPmeDonneurOrdre)
        .filter(RelationPmeDonneurOrdre.pme_id == facture.pme_id, RelationPmeDonneurOrdre.donneur_ordre_id == facture.donneur_ordre_id)
        .first()
    )

    cheque = facture.cheque_garantie
    cheque_out = (
        ChequeResumeOut(
            numero_cheque=cheque.numero_cheque,
            banque_emettrice=cheque.banque_emettrice,
            date_encaissement_prevue=cheque.date_encaissement_prevue,
            statut=cheque.statut,
        )
        if cheque is not None
        else None
    )

    enveloppe = (
        db.query(EnveloppePartenaire)
        .filter(EnveloppePartenaire.partenaire_financier_id == avance.partenaire_financier_id)
        .first()
    )
    enveloppe_disponible = None
    enveloppe_totale = None
    if enveloppe is not None:
        montant_engage = (
            db.query(func.coalesce(func.sum(Avance.montant_avance_initial), 0))
            .filter(Avance.partenaire_financier_id == avance.partenaire_financier_id, Avance.statut == StatutAvance.AVANCE_VERSEE)
            .scalar()
        )
        enveloppe_totale = enveloppe.montant_total_alloue
        enveloppe_disponible = enveloppe.montant_total_alloue - Decimal(montant_engage)

    limite = (
        db.query(LimiteCredit)
        .filter(
            LimiteCredit.partenaire_financier_id == avance.partenaire_financier_id,
            LimiteCredit.entreprise_cible_id == facture.donneur_ordre_id,
            LimiteCredit.type_limite == TypeLimite.ACHETEUR,
            LimiteCredit.active.is_(True),
        )
        .first()
    )

    historique = (
        db.query(Remboursement)
        .join(Avance, Avance.id == Remboursement.avance_id)
        .join(Facture, Facture.id == Avance.facture_id)
        .filter(Facture.donneur_ordre_id == facture.donneur_ordre_id, Remboursement.statut_rapprochement == "rapproche")
        .count()
    )

    grille = avance.grille_tarifaire
    # Taux total reellement applique a cette avance (le bareme est degressif selon la
    # duree, cf. app.services.calcul_frais) : recalcule a partir des montants figes plutot
    # que de relire un champ fixe de la grille, qui ne represente plus une valeur unique.
    taux_total_applique = (avance.frais_total / facture.montant_ttc) if facture.montant_ttc else Decimal("0")

    return DossierDecisionOut(
        avance=avance,
        numero_facture=facture.numero_facture,
        montant_ttc=facture.montant_ttc,
        date_emission=facture.date_emission,
        date_echeance=facture.date_echeance,
        duree_jours=facture.duree_jours,
        pme_raison_sociale=pme.raison_sociale,
        pme_statut_kyc=pme.statut_kyc,
        donneur_ordre_raison_sociale=donneur_ordre.raison_sociale,
        donneur_ordre_statut_kyc=donneur_ordre.statut_kyc,
        relation_statut=relation.statut if relation else None,
        cheque=cheque_out,
        enveloppe_disponible=enveloppe_disponible,
        enveloppe_totale=enveloppe_totale,
        limite_acheteur_plafond=limite.montant_plafond if limite else None,
        limite_acheteur_utilisee=limite.montant_utilise if limite else None,
        historique_cycles_rembourses=historique,
        grille_taux_total=taux_total_applique,
        grille_plafond_montant=grille.plafond_montant,
    )


@router.post("/{avance_id}/approuver", response_model=AvanceOut)
def approuver_avance(
    avance_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role([RoleUtilisateur.AGENT_FINANCIER])),
):
    avance = _get_avance_or_404(db, avance_id)
    if avance.statut != StatutAvance.EN_ATTENTE_VALIDATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossible d'approuver une avance au statut '{avance.statut.value}'",
        )
    if current_user.role != RoleUtilisateur.ADMIN and avance.partenaire_financier_id != current_user.entreprise_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette avance ne vous appartient pas")

    # Doc §3.3quater.2 : verification bloquante de l'enveloppe et des limites de credit
    # applicables, pas un simple avertissement — faite ici (a la decision), pas a la
    # demande de la PME qui n'a pas a connaitre l'enveloppe du partenaire.
    enveloppe = (
        db.query(EnveloppePartenaire)
        .filter(EnveloppePartenaire.partenaire_financier_id == avance.partenaire_financier_id)
        .first()
    )
    if enveloppe is not None:
        montant_engage = (
            db.query(func.coalesce(func.sum(Avance.montant_avance_initial), 0))
            .filter(Avance.partenaire_financier_id == avance.partenaire_financier_id, Avance.statut == StatutAvance.AVANCE_VERSEE)
            .scalar()
        )
        disponible = enveloppe.montant_total_alloue - Decimal(montant_engage)
        if avance.montant_avance_initial > disponible:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Enveloppe insuffisante : {disponible} FCFA disponibles pour {avance.montant_avance_initial} FCFA demandes",
            )

    limite_acheteur = (
        db.query(LimiteCredit)
        .filter(
            LimiteCredit.partenaire_financier_id == avance.partenaire_financier_id,
            LimiteCredit.entreprise_cible_id == avance.facture.donneur_ordre_id,
            LimiteCredit.type_limite == TypeLimite.ACHETEUR,
            LimiteCredit.active.is_(True),
        )
        .first()
    )
    if limite_acheteur is not None and limite_acheteur.montant_utilise + avance.montant_avance_initial > limite_acheteur.montant_plafond:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Limite de crédit atteinte sur ce donneur d'ordre",
        )

    avant = {"statut": avance.statut.value}
    avance.statut = StatutAvance.AVANCE_VERSEE
    avance.date_versement_initial = datetime.now(timezone.utc)
    avance.facture.statut = StatutFacture.AVANCE_VERSEE
    if limite_acheteur is not None:
        limite_acheteur.montant_utilise += avance.montant_avance_initial

    enregistrer_audit(
        db,
        entite_type="Avance",
        entite_id=avance.id,
        action="approbation",
        utilisateur_id=current_user.id,
        valeur_avant=avant,
        valeur_apres={"statut": avance.statut.value},
    )
    db.commit()
    db.refresh(avance)
    return avance


@router.post("/{avance_id}/rejeter", response_model=AvanceOut)
def rejeter_avance(
    avance_id: uuid.UUID,
    payload: AvanceRejetRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role([RoleUtilisateur.AGENT_FINANCIER])),
):
    avance = _get_avance_or_404(db, avance_id)
    if avance.statut != StatutAvance.EN_ATTENTE_VALIDATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossible de rejeter une avance au statut '{avance.statut.value}'",
        )

    avant = {"statut": avance.statut.value}
    avance.statut = StatutAvance.REJETEE
    avance.facture.statut = StatutFacture.VALIDEE

    enregistrer_audit(
        db,
        entite_type="Avance",
        entite_id=avance.id,
        action="rejet",
        utilisateur_id=current_user.id,
        valeur_avant=avant,
        valeur_apres={"statut": avance.statut.value, "commentaire": payload.commentaire},
    )
    db.commit()
    db.refresh(avance)
    return avance
