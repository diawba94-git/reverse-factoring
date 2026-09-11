from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.avance import Avance
from app.models.entreprise import Entreprise
from app.models.enums import RoleUtilisateur, StatutAvance, StatutFacture, StatutFiche, StatutKyc, StatutRapprochement
from app.models.facture import Facture
from app.models.litige_dossier import LitigeDossier
from app.models.remboursement import Remboursement
from app.models.utilisateur import Utilisateur
from app.models.validation_facture import ValidationFacture
from app.schemas.pme_notification import NotificationPmeOut

router = APIRouter(prefix="/pme", tags=["pme"])

_SEUIL_NON_LU = timedelta(hours=48)
_ROLE_PME = [RoleUtilisateur.MEMBRE_PME]


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


@router.get(
    "/notifications",
    response_model=list[NotificationPmeOut],
    summary="Notifications de la PME, synthetisees a partir des evenements reels",
    description=(
        "Aucune table Notification dediee : chaque entree reflete un etat reel (validation "
        "en attente, avance versee, remboursement recu, litige ouvert, fiche acheteur creee, "
        "KYC valide, invitation acceptee) au moment de l'appel. 'lu' est un heuristique base "
        "sur l'anciennete (>48h = lu), il n'y a pas d'accuse de lecture persiste pour ce MVP."
    ),
)
def notifications_pme(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLE_PME)),
):
    pme_id = current_user.entreprise_id
    maintenant = datetime.now(timezone.utc)
    notifications: list[NotificationPmeOut] = []

    factures = db.query(Facture).filter(Facture.pme_id == pme_id).all()
    factures_par_id = {f.id: f for f in factures}
    donneur_ids = {f.donneur_ordre_id for f in factures}
    donneurs = {e.id: e for e in db.query(Entreprise).filter(Entreprise.id.in_(donneur_ids)).all()} if donneur_ids else {}

    for f in factures:
        if f.statut not in (StatutFacture.EMISE, StatutFacture.VALIDATION_COMPLEMENTAIRE_REQUISE):
            continue
        derniere = (
            db.query(ValidationFacture)
            .filter(ValidationFacture.facture_id == f.id)
            .order_by(ValidationFacture.date_validation.desc())
            .first()
        )
        if not derniere:
            continue
        nom_donneur = donneurs[f.donneur_ordre_id].raison_sociale if f.donneur_ordre_id in donneurs else "—"
        date_evt = _aware(derniere.date_validation)
        notifications.append(
            NotificationPmeOut(
                type="validation",
                titre=f"Facture {f.numero_facture or '(brouillon)'} : 1 validation sur 2 requises",
                description=f"{nom_donneur} a validé, en attente du second validateur",
                date=date_evt,
                lu=(maintenant - date_evt) > _SEUIL_NON_LU,
            )
        )

    avances = db.query(Avance).join(Facture, Facture.id == Avance.facture_id).filter(Facture.pme_id == pme_id).all()
    for a in avances:
        f = factures_par_id.get(a.facture_id)
        if not f:
            continue
        if a.statut in (StatutAvance.AVANCE_VERSEE, StatutAvance.SOLDEE) and a.date_versement_initial:
            date_evt = _aware(a.date_versement_initial)
            notifications.append(
                NotificationPmeOut(
                    type="financement",
                    titre=f"Facture {f.numero_facture} avancée",
                    description=(
                        f"{a.montant_avance_initial:,.0f} FCFA versés (80%) — solde attendu après remboursement".replace(",", " ")
                    ),
                    date=date_evt,
                    lu=(maintenant - date_evt) > _SEUIL_NON_LU,
                )
            )
        for r in db.query(Remboursement).filter(
            Remboursement.avance_id == a.id, Remboursement.statut_rapprochement == StatutRapprochement.RAPPROCHE
        ):
            date_evt = _aware(datetime.combine(r.date_reception, datetime.min.time()))
            description = f"{r.montant_recu:,.0f} FCFA reçus".replace(",", " ")
            if a.statut == StatutAvance.SOLDEE:
                description = f"Solde de {r.montant_recu:,.0f} FCFA versé, facture soldée".replace(",", " ")
            notifications.append(
                NotificationPmeOut(
                    type="financement",
                    titre=f"Remboursement reçu — {f.numero_facture}",
                    description=description,
                    date=date_evt,
                    lu=(maintenant - date_evt) > _SEUIL_NON_LU,
                )
            )

    litiges = (
        db.query(LitigeDossier).join(Facture, Facture.id == LitigeDossier.facture_id).filter(Facture.pme_id == pme_id).all()
    )
    for l in litiges:
        f = factures_par_id.get(l.facture_id)
        date_evt = _aware(l.ouvert_le)
        notifications.append(
            NotificationPmeOut(
                type="litige",
                titre=f"Litige ouvert — {f.numero_facture if f else '—'}",
                description=l.description,
                date=date_evt,
                lu=(maintenant - date_evt) > _SEUIL_NON_LU,
            )
        )

    for e in db.query(Entreprise).filter(Entreprise.cree_par_entreprise_id == pme_id).all():
        date_evt = _aware(e.created_at)
        notifications.append(
            NotificationPmeOut(
                type="acheteur",
                titre=f"Nouvelle fiche acheteur créée — {e.raison_sociale}",
                description=(
                    "Invitation envoyée, en attente d'inscription et de KYC"
                    if e.statut_fiche == StatutFiche.PRE_INSCRITE
                    else f"{e.raison_sociale} est désormais une fiche active"
                ),
                date=date_evt,
                lu=(maintenant - date_evt) > _SEUIL_NON_LU,
            )
        )

    pme = db.query(Entreprise).filter(Entreprise.id == pme_id).first()
    if pme and pme.statut_kyc == StatutKyc.VALIDE:
        date_evt = _aware(pme.created_at)
        notifications.append(
            NotificationPmeOut(
                type="kyc",
                titre="KYC de votre entreprise validé",
                description=f"{pme.raison_sociale} a désormais un accès complet à la plateforme",
                date=date_evt,
                lu=(maintenant - date_evt) > _SEUIL_NON_LU,
            )
        )

    collegues = (
        db.query(Utilisateur)
        .filter(Utilisateur.entreprise_id == pme_id, Utilisateur.id != current_user.id, Utilisateur.compte_actif == True)  # noqa: E712
        .all()
    )
    for c in collegues:
        date_evt = _aware(c.date_creation)
        notifications.append(
            NotificationPmeOut(
                type="invitation",
                titre=f"Invitation acceptée — {c.nom or 'Collègue'}",
                description="Votre collègue a rejoint l'entreprise en tant que membre PME",
                date=date_evt,
                lu=(maintenant - date_evt) > _SEUIL_NON_LU,
            )
        )

    notifications.sort(key=lambda n: n.date, reverse=True)
    return notifications
