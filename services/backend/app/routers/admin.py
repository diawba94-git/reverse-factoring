import calendar
import secrets
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.avance import Avance
from app.models.entreprise import Entreprise
from app.models.enums import RoleUtilisateur, StatutAvance, StatutFacture, StatutFiche, TypeEntreprise
from app.models.facture import Facture
from app.models.journal_audit import JournalAudit
from app.models.remboursement import Remboursement
from app.models.utilisateur import RefreshToken, Utilisateur
from app.schemas.admin import (
    AdminCreerUtilisateurRequest,
    AdminModifierUtilisateurRequest,
    AdminUtilisateurCreeOut,
    JournalAuditOut,
    RapportPeriodeOut,
    RemboursementSuperviseOut,
    SessionOut,
    TransactionOut,
)
from app.schemas.doublon import DoublonCandidatOut, DoublonEntrepriseOut, FusionDoublonRequest, FusionDoublonResultOut
from app.schemas.utilisateur import UtilisateurOut
from app.security import hash_password
from app.services.audit import enregistrer_audit
from app.services.roles import ROLES_AUTORISES_PAR_TYPE

router = APIRouter(prefix="/admin", tags=["admin"])

_ROLES_ADMIN = [RoleUtilisateur.ADMIN]


def _verifier_role_autorise(role: RoleUtilisateur, entreprise: Entreprise) -> None:
    """Meme correspondance role/type que POST /entreprises/{id}/inviter (voir
    app.services.roles.ROLES_AUTORISES_PAR_TYPE) : le role `admin` n'y figure jamais, donc
    aucune des routes qui passent par ce garde-fou ne peut jamais l'attribuer."""
    roles_autorises = ROLES_AUTORISES_PAR_TYPE.get(entreprise.type, set())
    if role not in roles_autorises:
        labels = ", ".join(sorted(r.value for r in roles_autorises))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Le role '{role.value}' n'est pas attribuable pour une entreprise de type "
                f"'{entreprise.type.value}' (roles autorises : {labels})"
            ),
        )


@router.post(
    "/entreprises/{entreprise_id}/utilisateurs",
    response_model=AdminUtilisateurCreeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cree un utilisateur pour une entreprise, avec activation immediate (admin uniquement)",
    description=(
        "Reserve au role admin. Contrairement a POST /entreprises/{id}/inviter (auto-invitation "
        "entre collegues : compte_actif=false jusqu'a acceptation du token d'invitation), l'admin "
        "agit ici en tiers de confiance : le compte est actif immediatement, avec un mot de passe "
        "temporaire genere serveur cense etre communique par SMS/email."
    ),
)
def creer_utilisateur_admin(
    entreprise_id: uuid.UUID,
    payload: AdminCreerUtilisateurRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    entreprise = db.get(Entreprise, entreprise_id)
    if entreprise is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entreprise introuvable")

    _verifier_role_autorise(payload.role, entreprise)

    if db.query(Utilisateur).filter(Utilisateur.telephone == payload.telephone).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce numero de telephone est deja utilise")

    mot_de_passe_temporaire = secrets.token_urlsafe(9)
    utilisateur = Utilisateur(
        entreprise_id=entreprise.id,
        role=payload.role,
        nom=payload.nom,
        telephone=payload.telephone,
        email=payload.email,
        mot_de_passe_hash=hash_password(mot_de_passe_temporaire),
        compte_actif=True,
    )
    db.add(utilisateur)
    db.flush()

    enregistrer_audit(
        db,
        entite_type="Utilisateur",
        entite_id=utilisateur.id,
        action="creation_admin",
        utilisateur_id=current_user.id,
        valeur_apres={
            "telephone": utilisateur.telephone,
            "role": utilisateur.role.value,
            "entreprise_id": str(entreprise.id),
        },
    )
    db.commit()
    db.refresh(utilisateur)

    donnees = UtilisateurOut.model_validate(utilisateur).model_dump()
    return AdminUtilisateurCreeOut(**donnees, mot_de_passe_temporaire=mot_de_passe_temporaire)


@router.patch(
    "/utilisateurs/{utilisateur_id}",
    response_model=UtilisateurOut,
    summary="Modifie le role et/ou active/desactive un utilisateur (admin uniquement)",
    description=(
        "Le changement de role est revalide serveur contre le type de l'entreprise de "
        "l'utilisateur (voir app.services.roles.ROLES_AUTORISES_PAR_TYPE), exactement comme a "
        "la creation : le role `admin` n'est jamais atteignable via cette route."
    ),
)
def modifier_utilisateur_admin(
    utilisateur_id: uuid.UUID,
    payload: AdminModifierUtilisateurRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    utilisateur = db.get(Utilisateur, utilisateur_id)
    if utilisateur is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")

    if payload.role is not None and payload.role != utilisateur.role:
        _verifier_role_autorise(payload.role, utilisateur.entreprise)

    avant = {"role": utilisateur.role.value, "compte_actif": utilisateur.compte_actif}
    if payload.role is not None:
        utilisateur.role = payload.role
    if payload.compte_actif is not None:
        utilisateur.compte_actif = payload.compte_actif

    enregistrer_audit(
        db,
        entite_type="Utilisateur",
        entite_id=utilisateur.id,
        action="modification_admin",
        utilisateur_id=current_user.id,
        valeur_avant=avant,
        valeur_apres={"role": utilisateur.role.value, "compte_actif": utilisateur.compte_actif},
    )
    db.commit()
    db.refresh(utilisateur)
    return utilisateur


@router.get(
    "/utilisateurs/{utilisateur_id}/sessions",
    response_model=list[SessionOut],
    summary="Liste les sessions (refresh tokens) d'un utilisateur (admin uniquement)",
)
def lister_sessions_utilisateur(
    utilisateur_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    if db.get(Utilisateur, utilisateur_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    return (
        db.query(RefreshToken)
        .filter(RefreshToken.utilisateur_id == utilisateur_id)
        .order_by(RefreshToken.created_at.desc())
        .all()
    )


@router.post(
    "/sessions/{session_id}/revoquer",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoque une session (refresh token) precise (admin uniquement)",
)
def revoquer_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    session_token = db.get(RefreshToken, session_id)
    if session_token is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session introuvable")
    session_token.revoked = True
    enregistrer_audit(
        db,
        entite_type="RefreshToken",
        entite_id=session_token.id,
        action="revocation",
        utilisateur_id=current_user.id,
        valeur_apres={"utilisateur_id": str(session_token.utilisateur_id)},
    )
    db.commit()


@router.post(
    "/utilisateurs/{utilisateur_id}/sessions/revoquer-tout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoque toutes les sessions actives d'un utilisateur (admin uniquement)",
)
def revoquer_toutes_les_sessions(
    utilisateur_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    if db.get(Utilisateur, utilisateur_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    sessions = (
        db.query(RefreshToken)
        .filter(RefreshToken.utilisateur_id == utilisateur_id, RefreshToken.revoked.is_(False))
        .all()
    )
    for session_token in sessions:
        session_token.revoked = True
    enregistrer_audit(
        db,
        entite_type="Utilisateur",
        entite_id=utilisateur_id,
        action="revocation_sessions",
        utilisateur_id=current_user.id,
        valeur_apres={"nombre_sessions_revoquees": len(sessions)},
    )
    db.commit()


@router.get(
    "/journal-audit",
    response_model=list[JournalAuditOut],
    summary="Consulte le journal d'audit applicatif (admin uniquement)",
)
def lister_journal_audit(
    entite_type: str | None = None,
    action: str | None = None,
    limite: int = 200,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    query = db.query(JournalAudit)
    if entite_type is not None:
        query = query.filter(JournalAudit.entite_type == entite_type)
    if action is not None:
        query = query.filter(JournalAudit.action == action)
    return query.order_by(JournalAudit.horodatage.desc()).limit(min(limite, 500)).all()


@router.get(
    "/transactions",
    response_model=list[TransactionOut],
    summary="Vue consolidee facture + avance a des fins de supervision (admin uniquement)",
)
def superviser_transactions(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    # Un brouillon n'a pas encore ete transmis au donneur d'ordre (ni numero, ni
    # engagement reel) : il n'a pas sa place dans une vue de supervision des transactions.
    lignes = (
        db.query(Facture)
        .filter(Facture.statut != StatutFacture.BROUILLON)
        .order_by(Facture.created_at.desc())
        .limit(500)
        .all()
    )
    return [
        TransactionOut(
            facture_id=facture.id,
            numero_facture=facture.numero_facture,
            fournisseur=facture.pme.raison_sociale,
            acheteur=facture.donneur_ordre.raison_sociale,
            montant=facture.montant_ttc,
            etape=facture.avance.statut.value if facture.avance else facture.statut.value,
            avance_id=facture.avance.id if facture.avance else None,
        )
        for facture in lignes
    ]


@router.get(
    "/remboursements",
    response_model=list[RemboursementSuperviseOut],
    summary="Vue consolidee des remboursements pour la reconciliation bancaire (admin uniquement)",
)
def superviser_remboursements(
    response: Response,
    statut_rapprochement: str | None = None,
    page: int | None = None,
    per_page: int | None = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    query = db.query(Remboursement)
    if statut_rapprochement is not None:
        query = query.filter(Remboursement.statut_rapprochement == statut_rapprochement)
    query = query.order_by(Remboursement.created_at.desc())

    if page is not None or per_page is not None:
        page = page or 1
        per_page = per_page or 25
        response.headers["X-Total-Count"] = str(query.count())
        query = query.offset((page - 1) * per_page).limit(per_page)
    else:
        query = query.limit(500)

    remboursements = query.all()
    return [
        RemboursementSuperviseOut(
            id=r.id,
            avance_id=r.avance_id,
            montant_recu=r.montant_recu,
            date_reception=r.date_reception,
            source_entreprise=r.source_entreprise.raison_sociale,
            montant_attendu=r.avance.montant_solde_du,
            ecart=r.montant_recu - r.avance.montant_solde_du,
            statut_rapprochement=r.statut_rapprochement.value,
        )
        for r in remboursements
    ]


def _bornes_periode(periode: str) -> tuple[date, date]:
    aujourdhui = date.today()
    if periode == "mois":
        debut = aujourdhui.replace(day=1)
        fin = date(debut.year, debut.month, calendar.monthrange(debut.year, debut.month)[1])
        return debut, fin
    if periode == "trimestre":
        trimestre = (aujourdhui.month - 1) // 3
        premier_mois = trimestre * 3 + 1
        dernier_mois = premier_mois + 2
        debut = date(aujourdhui.year, premier_mois, 1)
        fin = date(aujourdhui.year, dernier_mois, calendar.monthrange(aujourdhui.year, dernier_mois)[1])
        return debut, fin
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Periode invalide (mois ou trimestre)")


@router.get(
    "/rapports",
    response_model=RapportPeriodeOut,
    summary="Rapport consolide sur une periode (admin uniquement)",
)
def rapport_periode(
    periode: str = "mois",
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    debut, fin = _bornes_periode(periode)
    debut_dt = datetime.combine(debut, datetime.min.time(), tzinfo=timezone.utc)
    fin_dt = datetime.combine(fin, datetime.max.time(), tzinfo=timezone.utc)

    factures_query = db.query(Facture).filter(Facture.date_emission.between(debut, fin))
    nombre_factures = factures_query.count()
    montant_total_factures = factures_query.with_entities(func.coalesce(func.sum(Facture.montant_ttc), 0)).scalar()

    avances_query = db.query(Avance).filter(Avance.created_at.between(debut_dt, fin_dt))
    nombre_avances = avances_query.count()
    montant_total_avance_verse = (
        avances_query.filter(Avance.statut.in_([StatutAvance.AVANCE_VERSEE, StatutAvance.SOLDEE, StatutAvance.EN_DEFAUT]))
        .with_entities(func.coalesce(func.sum(Avance.montant_avance_initial), 0))
        .scalar()
    )
    montant_total_frais_plateforme = (
        avances_query.filter(Avance.statut.in_([StatutAvance.AVANCE_VERSEE, StatutAvance.SOLDEE]))
        .with_entities(func.coalesce(func.sum(Avance.part_plateforme), 0))
        .scalar()
    )
    montant_total_rembourse = (
        db.query(func.coalesce(func.sum(Remboursement.montant_recu), 0))
        .filter(Remboursement.date_reception.between(debut, fin))
        .scalar()
    )

    return RapportPeriodeOut(
        periode=periode,
        debut=debut,
        fin=fin,
        nombre_factures=nombre_factures,
        montant_total_factures=Decimal(montant_total_factures),
        nombre_avances=nombre_avances,
        montant_total_avance_verse=Decimal(montant_total_avance_verse),
        montant_total_frais_plateforme=Decimal(montant_total_frais_plateforme),
        montant_total_rembourse=Decimal(montant_total_rembourse),
    )


_SEUIL_SIMILARITE = 0.72


def _resume_doublon(db: Session, entreprise: Entreprise) -> DoublonEntrepriseOut:
    cree_par = None
    if entreprise.cree_par_entreprise_id is not None:
        createur = db.get(Entreprise, entreprise.cree_par_entreprise_id)
        cree_par = createur.raison_sociale if createur is not None else None
    nombre_factures = db.query(Facture).filter(Facture.donneur_ordre_id == entreprise.id).count()
    return DoublonEntrepriseOut(
        id=entreprise.id,
        raison_sociale=entreprise.raison_sociale,
        statut_fiche=entreprise.statut_fiche,
        statut_kyc=entreprise.statut_kyc,
        contact_telephone=entreprise.contact_telephone,
        cree_par=cree_par,
        nombre_factures=nombre_factures,
    )


@router.get(
    "/doublons/detecter",
    response_model=list[DoublonCandidatOut],
    summary="Detecte les fiches acheteur probablement en doublon (admin uniquement)",
    description=(
        "Scan a la volee (pas de table persistee) : similarite de nom + egalite de "
        "telephone entre entreprises GRANDE_ENTREPRISE actives, exactement le mecanisme "
        "decrit en architecture-mvp-affacturage-inverse.md §3.5.4."
    ),
)
def detecter_doublons(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    acheteurs = (
        db.query(Entreprise)
        .filter(Entreprise.type == TypeEntreprise.GRANDE_ENTREPRISE, Entreprise.actif.is_(True))
        .order_by(Entreprise.created_at.asc())
        .all()
    )

    candidats: list[DoublonCandidatOut] = []
    for i, a in enumerate(acheteurs):
        for b in acheteurs[i + 1 :]:
            nom_a, nom_b = a.raison_sociale.strip().lower(), b.raison_sociale.strip().lower()
            ratio = SequenceMatcher(None, nom_a, nom_b).ratio()
            meme_telephone = bool(a.contact_telephone) and a.contact_telephone == b.contact_telephone

            if not meme_telephone and ratio < _SEUIL_SIMILARITE:
                continue

            if meme_telephone and ratio >= _SEUIL_SIMILARITE:
                critere = "nom + telephone"
            elif meme_telephone:
                critere = "telephone seul"
            else:
                critere = "nom seul"
            score = max(ratio, 0.9) if meme_telephone else ratio

            # Suggestion : garder la fiche ACTIVE (creee via son propre onboarding) plutot
            # que celle PRE_INSCRITE (creee ad-hoc par une PME) ; a egalite, la plus ancienne.
            if a.statut_fiche == b.statut_fiche:
                conserver, fusionner = (a, b) if a.created_at <= b.created_at else (b, a)
            elif a.statut_fiche == StatutFiche.ACTIVE:
                conserver, fusionner = a, b
            else:
                conserver, fusionner = b, a

            candidats.append(
                DoublonCandidatOut(
                    conserver=_resume_doublon(db, conserver),
                    fusionner=_resume_doublon(db, fusionner),
                    score_similarite=round(score, 2),
                    critere=critere,
                )
            )

    candidats.sort(key=lambda c: c.score_similarite, reverse=True)
    return candidats


@router.post(
    "/doublons/fusionner",
    response_model=FusionDoublonResultOut,
    summary="Fusionne deux fiches acheteur en doublon (admin uniquement, action irreversible)",
    description=(
        "Reassigne toutes les Facture.donneur_ordre_id et tous les Utilisateur.entreprise_id "
        "de la fiche fusionnee vers la fiche conservee, puis desactive la fiche fusionnee "
        "(jamais supprimee, pour garder la tracabilite) — architecture-mvp-affacturage-inverse.md §3.5.4."
    ),
)
def fusionner_doublons(
    payload: FusionDoublonRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    if payload.conserver_id == payload.fusionner_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Les deux fiches sont identiques")

    conserver = db.get(Entreprise, payload.conserver_id)
    fusionner = db.get(Entreprise, payload.fusionner_id)
    if conserver is None or fusionner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fiche entreprise introuvable")
    if conserver.type != TypeEntreprise.GRANDE_ENTREPRISE or fusionner.type != TypeEntreprise.GRANDE_ENTREPRISE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La fusion de doublons n'est disponible que pour des fiches acheteur (GRANDE_ENTREPRISE)",
        )
    if not fusionner.actif:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette fiche est deja fusionnee/desactivee")

    nb_factures = (
        db.query(Facture)
        .filter(Facture.donneur_ordre_id == fusionner.id)
        .update({"donneur_ordre_id": conserver.id}, synchronize_session=False)
    )
    nb_utilisateurs = (
        db.query(Utilisateur)
        .filter(Utilisateur.entreprise_id == fusionner.id)
        .update({"entreprise_id": conserver.id}, synchronize_session=False)
    )
    fusionner.actif = False

    enregistrer_audit(
        db,
        entite_type="Entreprise",
        entite_id=fusionner.id,
        action="fusion_doublon",
        utilisateur_id=current_user.id,
        valeur_apres={
            "conserver_id": str(conserver.id),
            "factures_reassignees": nb_factures,
            "utilisateurs_reassignes": nb_utilisateurs,
        },
    )
    db.commit()

    return FusionDoublonResultOut(
        conserver_id=conserver.id,
        fusionner_id=fusionner.id,
        factures_reassignees=nb_factures,
        utilisateurs_reassignes=nb_utilisateurs,
    )
