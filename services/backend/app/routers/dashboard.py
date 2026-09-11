import uuid
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.avance import Avance
from app.models.entreprise import Entreprise
from app.models.enums import RoleUtilisateur, StatutAvance, StatutFacture, StatutTicket, TypeEntreprise
from app.models.facture import Facture
from app.models.remboursement import Remboursement
from app.models.score_donneur_ordre import ScoreDonneurOrdre
from app.models.ticket_support import TicketSupport
from app.models.utilisateur import Utilisateur
from app.schemas.dashboard import DashboardAdminOut, DashboardDonneurOrdreOut, DashboardPartenaireOut, DashboardPmeOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_ROLES_ADMIN = {RoleUtilisateur.ADMIN}


def _check_acces_entreprise(current_user: Utilisateur, entreprise_id: uuid.UUID) -> None:
    if current_user.role in _ROLES_ADMIN:
        return
    if current_user.entreprise_id != entreprise_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse a ce tableau de bord")


@router.get("/pme/{entreprise_id}", response_model=DashboardPmeOut)
def dashboard_pme(
    entreprise_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    _check_acces_entreprise(current_user, entreprise_id)

    # Les brouillons ne sont pas encore emis (aucun engagement envers un donneur d'ordre) :
    # ils sont exclus des indicateurs, mais restent visibles dans factures_par_statut pour
    # que la PME retrouve ses brouillons en attente de transmission.
    factures_par_statut = dict(
        db.query(Facture.statut, func.count(Facture.id))
        .filter(Facture.pme_id == entreprise_id)
        .group_by(Facture.statut)
        .all()
    )
    factures_par_statut = {k.value: v for k, v in factures_par_statut.items()}

    nombre_factures = sum(v for k, v in factures_par_statut.items() if k != StatutFacture.BROUILLON.value)
    montant_total_factures = (
        db.query(func.coalesce(func.sum(Facture.montant_ttc), 0))
        .filter(Facture.pme_id == entreprise_id, Facture.statut != StatutFacture.BROUILLON)
        .scalar()
    )

    avances_query = db.query(Avance).join(Facture, Facture.id == Avance.facture_id).filter(
        Facture.pme_id == entreprise_id
    )
    nombre_avances_actives = avances_query.filter(
        Avance.statut.in_([StatutAvance.AVANCE_VERSEE, StatutAvance.EN_ATTENTE_VALIDATION])
    ).count()
    montant_total_avance_percu = (
        db.query(func.coalesce(func.sum(Avance.montant_avance_initial), 0))
        .join(Facture, Facture.id == Avance.facture_id)
        .filter(Facture.pme_id == entreprise_id)
        .filter(Avance.statut.in_([StatutAvance.AVANCE_VERSEE, StatutAvance.SOLDEE]))
        .scalar()
    )
    montant_total_solde_du = (
        db.query(func.coalesce(func.sum(Avance.montant_solde_du), 0))
        .join(Facture, Facture.id == Avance.facture_id)
        .filter(Facture.pme_id == entreprise_id)
        .filter(Avance.statut == StatutAvance.AVANCE_VERSEE)
        .scalar()
    )

    return DashboardPmeOut(
        nombre_factures=nombre_factures,
        montant_total_factures=Decimal(montant_total_factures),
        factures_par_statut=factures_par_statut,
        nombre_avances_actives=nombre_avances_actives,
        montant_total_avance_percu=Decimal(montant_total_avance_percu),
        montant_total_solde_du=Decimal(montant_total_solde_du),
    )


@router.get("/donneur-ordre/{entreprise_id}", response_model=DashboardDonneurOrdreOut)
def dashboard_donneur_ordre(
    entreprise_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    _check_acces_entreprise(current_user, entreprise_id)

    factures_par_statut = dict(
        db.query(Facture.statut, func.count(Facture.id))
        .filter(Facture.donneur_ordre_id == entreprise_id)
        .group_by(Facture.statut)
        .all()
    )
    factures_par_statut = {k.value: v for k, v in factures_par_statut.items()}
    nombre_factures = sum(factures_par_statut.values())
    montant_total_factures = (
        db.query(func.coalesce(func.sum(Facture.montant_ttc), 0))
        .filter(Facture.donneur_ordre_id == entreprise_id)
        .scalar()
    )

    dernier_score = (
        db.query(ScoreDonneurOrdre)
        .filter(ScoreDonneurOrdre.entreprise_id == entreprise_id)
        .order_by(ScoreDonneurOrdre.date_calcul.desc())
        .first()
    )

    return DashboardDonneurOrdreOut(
        nombre_factures=nombre_factures,
        montant_total_factures=Decimal(montant_total_factures),
        factures_par_statut=factures_par_statut,
        score_actuel=dernier_score.score if dernier_score else None,
    )


@router.get("/partenaire/{entreprise_id}", response_model=DashboardPartenaireOut)
def dashboard_partenaire(
    entreprise_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    _check_acces_entreprise(current_user, entreprise_id)

    avances_par_statut = dict(
        db.query(Avance.statut, func.count(Avance.id))
        .filter(Avance.partenaire_financier_id == entreprise_id)
        .group_by(Avance.statut)
        .all()
    )
    avances_par_statut = {k.value: v for k, v in avances_par_statut.items()}
    nombre_avances = sum(avances_par_statut.values())

    montant_total_avance = (
        db.query(func.coalesce(func.sum(Avance.montant_avance_initial), 0))
        .filter(Avance.partenaire_financier_id == entreprise_id)
        .filter(Avance.statut.in_([StatutAvance.AVANCE_VERSEE, StatutAvance.SOLDEE, StatutAvance.EN_DEFAUT]))
        .scalar()
    )
    montant_total_rembourse = (
        db.query(func.coalesce(func.sum(Remboursement.montant_recu), 0))
        .join(Avance, Avance.id == Remboursement.avance_id)
        .filter(Avance.partenaire_financier_id == entreprise_id)
        .scalar()
    )
    montant_en_defaut = (
        db.query(func.coalesce(func.sum(Avance.montant_solde_du), 0))
        .filter(Avance.partenaire_financier_id == entreprise_id)
        .filter(Avance.statut == StatutAvance.EN_DEFAUT)
        .scalar()
    )
    encours = (
        db.query(func.coalesce(func.sum(Avance.montant_avance_initial), 0))
        .filter(Avance.partenaire_financier_id == entreprise_id)
        .filter(Avance.statut == StatutAvance.AVANCE_VERSEE)
        .scalar()
    )

    return DashboardPartenaireOut(
        nombre_avances=nombre_avances,
        avances_par_statut=avances_par_statut,
        montant_total_avance=Decimal(montant_total_avance),
        montant_total_rembourse=Decimal(montant_total_rembourse),
        montant_en_defaut=Decimal(montant_en_defaut),
        encours=Decimal(encours),
    )


def _debut_semaine(jour: date) -> date:
    return jour - timedelta(days=jour.weekday())


def _debut_mois(jour: date) -> date:
    return jour.replace(day=1)


@router.get("/admin", response_model=DashboardAdminOut)
def dashboard_admin(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(list(_ROLES_ADMIN))),
):
    entreprises_par_type = dict(db.query(Entreprise.type, func.count(Entreprise.id)).group_by(Entreprise.type).all())
    entreprises_par_type = {k.value: v for k, v in entreprises_par_type.items()}

    montant_total_avance_verse = (
        db.query(func.coalesce(func.sum(Avance.montant_avance_initial), 0))
        .filter(Avance.statut.in_([StatutAvance.AVANCE_VERSEE, StatutAvance.SOLDEE, StatutAvance.EN_DEFAUT]))
        .scalar()
    )
    montant_total_frais_plateforme = (
        db.query(func.coalesce(func.sum(Avance.part_plateforme), 0))
        .filter(Avance.statut.in_([StatutAvance.AVANCE_VERSEE, StatutAvance.SOLDEE]))
        .scalar()
    )

    # --- Tendances (8 semaines glissantes, calculees en Python a partir des created_at
    # reels : volume de donnees modeste au MVP, pas besoin de date_trunc SQL). ---
    aujourdhui = date.today()
    semaines = [_debut_semaine(aujourdhui) - timedelta(weeks=i) for i in range(7, -1, -1)]

    entreprises_dates = db.query(Entreprise.type, Entreprise.created_at).all()
    evolution_entreprises_hebdo: dict[str, list[int]] = {t.value: [0] * 8 for t in TypeEntreprise}
    entreprises_creees_ce_mois: dict[str, int] = {t.value: 0 for t in TypeEntreprise}
    debut_mois = _debut_mois(aujourdhui)
    for type_entreprise, created_at in entreprises_dates:
        jour = created_at.date()
        if jour >= debut_mois:
            entreprises_creees_ce_mois[type_entreprise.value] += 1
        semaine = _debut_semaine(jour)
        if semaine in semaines:
            evolution_entreprises_hebdo[type_entreprise.value][semaines.index(semaine)] += 1

    avances_dates = (
        db.query(Avance.montant_avance_initial, Avance.created_at)
        .filter(Avance.statut.in_([StatutAvance.AVANCE_VERSEE, StatutAvance.SOLDEE, StatutAvance.EN_DEFAUT]))
        .all()
    )
    evolution_volume_hebdo = [Decimal("0")] * 8
    volume_mois_courant = Decimal("0")
    volume_mois_precedent = Decimal("0")
    mois_precedent_fin = debut_mois - timedelta(days=1)
    mois_precedent_debut = _debut_mois(mois_precedent_fin)
    for montant, created_at in avances_dates:
        jour = created_at.date()
        semaine = _debut_semaine(jour)
        if semaine in semaines:
            evolution_volume_hebdo[semaines.index(semaine)] += montant
        if jour >= debut_mois:
            volume_mois_courant += montant
        elif mois_precedent_debut <= jour <= mois_precedent_fin:
            volume_mois_precedent += montant

    delta_volume_pourcentage = (
        ((volume_mois_courant - volume_mois_precedent) / volume_mois_precedent * 100)
        if volume_mois_precedent > 0
        else None
    )

    avances_reparties = (
        db.query(Avance.montant_avance_initial, Avance.montant_solde_du, Avance.part_partenaire, Avance.part_plateforme)
        .filter(Avance.statut.in_([StatutAvance.AVANCE_VERSEE, StatutAvance.SOLDEE, StatutAvance.EN_DEFAUT]))
        .all()
    )
    repartition_volume = {
        "pme": sum((a[0] + a[1] for a in avances_reparties), Decimal("0")),
        "partenaire": sum((a[2] for a in avances_reparties), Decimal("0")),
        "plateforme": sum((a[3] for a in avances_reparties), Decimal("0")),
    }

    return DashboardAdminOut(
        nombre_entreprises=db.query(func.count(Entreprise.id)).scalar(),
        entreprises_par_type=entreprises_par_type,
        entreprises_creees_ce_mois=entreprises_creees_ce_mois,
        evolution_entreprises_hebdo=evolution_entreprises_hebdo,
        evolution_volume_hebdo=evolution_volume_hebdo,
        nombre_utilisateurs=db.query(func.count(Utilisateur.id)).scalar(),
        nombre_factures=db.query(func.count(Facture.id)).scalar(),
        nombre_avances=db.query(func.count(Avance.id)).scalar(),
        montant_total_avance_verse=Decimal(montant_total_avance_verse),
        montant_total_avance_verse_delta_pourcentage=delta_volume_pourcentage,
        montant_total_frais_plateforme=Decimal(montant_total_frais_plateforme),
        repartition_volume=repartition_volume,
        tickets_ouverts=db.query(func.count(TicketSupport.id))
        .filter(TicketSupport.statut.in_([StatutTicket.OUVERT, StatutTicket.EN_COURS]))
        .scalar(),
    )
