import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.entreprise import Entreprise
from app.models.enums import RoleUtilisateur, StatutFacture, StatutFiche, StatutKyc, TypeEntreprise
from app.models.facture import Facture
from app.models.invitation import Invitation
from app.models.utilisateur import Utilisateur
from app.schemas.auth import InvitationOut, InviterRequest
from app.schemas.entreprise import (
    EntrepriseCreate,
    EntrepriseOut,
    EntrepriseUpdate,
    FicheMinimaleCreate,
    FicheMinimaleOut,
    KycStatutUpdate,
    KycUploadResponse,
)
from app.security import hash_password
from app.services.audit import enregistrer_audit
from app.services.kyc import rccm_est_obligatoire
from app.services.relations import copier_affectations
from app.services.roles import ROLES_AUTORISES_PAR_TYPE

router = APIRouter(prefix="/entreprises", tags=["entreprises"])

_UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads" / "kyc"

_ROLES_ADMIN = [RoleUtilisateur.ADMIN]

_ROLES_INVITEURS = [
    RoleUtilisateur.MEMBRE_PME,
    RoleUtilisateur.VALIDATEUR_1,
    RoleUtilisateur.VALIDATEUR_2,
    RoleUtilisateur.AGENT_FINANCIER,
]

_DUREE_VALIDITE_INVITATION = timedelta(days=7)


def _get_entreprise_or_404(db: Session, entreprise_id: uuid.UUID) -> Entreprise:
    entreprise = db.get(Entreprise, entreprise_id)
    if entreprise is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entreprise introuvable")
    return entreprise


def _check_membre_ou_admin(entreprise: Entreprise, current_user: Utilisateur) -> None:
    if current_user.role in _ROLES_ADMIN:
        return
    if current_user.entreprise_id != entreprise.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse a cette entreprise")


def _documents_manquants_kyc(entreprise: Entreprise) -> list[str]:
    """Liste, dans l'ordre, les elements du dossier KYC qui manquent encore pour que
    l'entreprise puisse passer en statut_kyc=valide. A appeler seulement une fois
    entreprise.forme_juridique confirme non nul par l'appelant."""
    manquants: list[str] = []
    if not entreprise.ninea:
        manquants.append("NINEA")
    if not entreprise.kyc_document_url:
        manquants.append("piece d'identite du representant (document KYC televerse)")
    if rccm_est_obligatoire(entreprise.forme_juridique) and not entreprise.rccm:
        manquants.append("RCCM")
    return manquants


@router.post("", response_model=EntrepriseOut, status_code=status.HTTP_201_CREATED)
def creer_entreprise(payload: EntrepriseCreate, db: Session = Depends(get_db)):
    entreprise = Entreprise(**payload.model_dump())
    db.add(entreprise)
    db.flush()
    enregistrer_audit(
        db,
        entite_type="Entreprise",
        entite_id=entreprise.id,
        action="creation",
        utilisateur_id=None,
        valeur_apres={"raison_sociale": entreprise.raison_sociale, "type": entreprise.type.value},
    )
    db.commit()
    db.refresh(entreprise)
    return entreprise


@router.post(
    "/fiche-minimale",
    response_model=FicheMinimaleOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cree une fiche acheteur minimale pour un acheteur pas encore present sur Cedra",
    description=(
        "Reserve a membre_pme/admin. Cree une Entreprise GRANDE_ENTREPRISE en statut_fiche "
        "pre_inscrite (cree_par_entreprise_id = la PME appelante) — voir doc §3.0quater, cas B. "
        "Les factures adressees a cette fiche restent au statut en_attente_kyc_acheteur jusqu'a "
        "ce que l'acheteur complete son propre onboarding et soit valide par l'admin."
    ),
)
def creer_fiche_minimale(
    payload: FicheMinimaleCreate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role([RoleUtilisateur.MEMBRE_PME, RoleUtilisateur.ADMIN])),
):
    entreprise = Entreprise(
        type=TypeEntreprise.GRANDE_ENTREPRISE,
        raison_sociale=payload.raison_sociale,
        statut_kyc=StatutKyc.EN_ATTENTE,
        statut_fiche=StatutFiche.PRE_INSCRITE,
        cree_par_entreprise_id=current_user.entreprise_id,
        contact_invitation_nom=payload.contact_invitation_nom,
        contact_invitation_email=payload.contact_invitation_email,
        date_invitation_envoyee=datetime.now(timezone.utc),
        token_invitation_initiale=secrets.token_urlsafe(32),
    )
    db.add(entreprise)
    db.flush()
    enregistrer_audit(
        db,
        entite_type="Entreprise",
        entite_id=entreprise.id,
        action="creation_fiche_minimale",
        utilisateur_id=current_user.id,
        valeur_apres={"raison_sociale": entreprise.raison_sociale, "cree_par": str(current_user.entreprise_id)},
    )
    db.commit()
    db.refresh(entreprise)
    donnees = EntrepriseOut.model_validate(entreprise).model_dump()
    return FicheMinimaleOut(**donnees, token_invitation=entreprise.token_invitation_initiale)


@router.get("", response_model=list[EntrepriseOut])
def lister_entreprises(
    type: TypeEntreprise | None = None,
    statut_kyc: StatutKyc | None = None,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    query = db.query(Entreprise)
    if type is not None:
        query = query.filter(Entreprise.type == type)
    if statut_kyc is not None:
        query = query.filter(Entreprise.statut_kyc == statut_kyc)
    return query.order_by(Entreprise.created_at.desc()).all()


@router.get("/{entreprise_id}", response_model=EntrepriseOut)
def obtenir_entreprise(
    entreprise_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    return _get_entreprise_or_404(db, entreprise_id)


@router.put("/{entreprise_id}", response_model=EntrepriseOut)
def modifier_entreprise(
    entreprise_id: uuid.UUID,
    payload: EntrepriseUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    entreprise = _get_entreprise_or_404(db, entreprise_id)
    _check_membre_ou_admin(entreprise, current_user)

    avant = {"raison_sociale": entreprise.raison_sociale, "contact_email": entreprise.contact_email}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entreprise, field, value)

    enregistrer_audit(
        db,
        entite_type="Entreprise",
        entite_id=entreprise.id,
        action="modification",
        utilisateur_id=current_user.id,
        valeur_avant=avant,
        valeur_apres=payload.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(entreprise)
    return entreprise


@router.delete("/{entreprise_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_entreprise(
    entreprise_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    entreprise = _get_entreprise_or_404(db, entreprise_id)
    db.delete(entreprise)
    enregistrer_audit(
        db,
        entite_type="Entreprise",
        entite_id=entreprise.id,
        action="suppression",
        utilisateur_id=current_user.id,
        valeur_apres={"raison_sociale": entreprise.raison_sociale},
    )
    db.commit()


@router.post(
    "/{entreprise_id}/inviter",
    response_model=InvitationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Invite un collegue dans sa propre entreprise",
    description=(
        "Accessible aux roles membre_pme, validateur_1, validateur_2 et agent_financier "
        "(jamais a un compte dont l'entreprise n'est pas encore validee cote KYC ; jamais "
        "pour attribuer le role `admin`). Le role demande est verifie contre le type de "
        "l'entreprise de l'appelant : une PME ne peut inviter qu'en `membre_pme`, une "
        "GRANDE_ENTREPRISE qu'en `validateur_1` ou `validateur_2` (les deux etant "
        "necessaires pour valider une facture, une entreprise peut avoir plusieurs "
        "utilisateurs de chaque), un PARTENAIRE_FINANCIER qu'en `agent_financier`. "
        "L'invitation cree immediatement un compte inactif (compte_actif=false) rattache a "
        "l'entreprise de l'inviteur ; l'invite l'active via POST "
        "/auth/accepter-invitation/{token} pour definir son mot de passe."
    ),
)
def inviter_utilisateur(
    entreprise_id: uuid.UUID,
    payload: InviterRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_INVITEURS)),
):
    if current_user.entreprise_id != entreprise_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez inviter que dans votre propre entreprise",
        )

    entreprise = current_user.entreprise
    # Exception au garde-fou habituel : un acheteur en cours d'onboarding (fiche minimale
    # pre_inscrite) doit pouvoir inviter son second validateur AVANT que le KYC ne soit
    # valide — c'est justement l'etape qui precede la soumission du dossier KYC (doc
    # §3.0quinquies.2). Toute entreprise deja active reste soumise au garde-fou normal.
    if entreprise.statut_kyc != StatutKyc.VALIDE and entreprise.statut_fiche != StatutFiche.PRE_INSCRITE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Votre entreprise doit etre validee (KYC) avant de pouvoir inviter des collegues",
        )

    roles_autorises = ROLES_AUTORISES_PAR_TYPE.get(entreprise.type, set())
    if payload.role not in roles_autorises:
        labels = ", ".join(sorted(r.value for r in roles_autorises))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Le role '{payload.role.value}' n'est pas attribuable pour une entreprise "
                f"de type '{entreprise.type.value}' (roles autorises : {labels})"
            ),
        )

    if db.query(Utilisateur).filter(Utilisateur.telephone == payload.telephone).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce numero de telephone est deja utilise")

    utilisateur = Utilisateur(
        entreprise_id=entreprise.id,
        role=payload.role,
        nom=payload.nom,
        telephone=payload.telephone,
        email=payload.email,
        # Placeholder inutilisable : personne ne peut se connecter avec ce mot de passe
        # (secret aleatoire jamais communique), et compte_actif=False bloque de toute facon
        # la connexion tant que l'invitation n'est pas acceptee.
        mot_de_passe_hash=hash_password(secrets.token_urlsafe(32)),
        compte_actif=False,
    )
    db.add(utilisateur)
    db.flush()

    if payload.role in (RoleUtilisateur.VALIDATEUR_1, RoleUtilisateur.VALIDATEUR_2):
        copier_affectations(db, depuis_utilisateur=current_user, vers_utilisateur_id=utilisateur.id)

    invitation = Invitation(
        utilisateur_id=utilisateur.id,
        invite_par_id=current_user.id,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.now(timezone.utc) + _DUREE_VALIDITE_INVITATION,
    )
    db.add(invitation)
    db.flush()

    enregistrer_audit(
        db,
        entite_type="Utilisateur",
        entite_id=utilisateur.id,
        action="invitation",
        utilisateur_id=current_user.id,
        valeur_apres={"telephone": utilisateur.telephone, "role": utilisateur.role.value},
    )
    db.commit()

    return InvitationOut(
        id=invitation.id,
        utilisateur_id=utilisateur.id,
        entreprise_id=entreprise.id,
        telephone=utilisateur.telephone,
        email=utilisateur.email,
        nom=utilisateur.nom,
        role=utilisateur.role,
        expires_at=invitation.expires_at,
        token=invitation.token,
    )


@router.post("/{entreprise_id}/kyc", response_model=KycUploadResponse)
async def televerser_kyc(
    entreprise_id: uuid.UUID,
    fichier: UploadFile,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    entreprise = _get_entreprise_or_404(db, entreprise_id)
    _check_membre_ou_admin(entreprise, current_user)

    if entreprise.type == TypeEntreprise.GRANDE_ENTREPRISE and entreprise.statut_fiche == StatutFiche.PRE_INSCRITE:
        # Doc §3.0quinquies.5 : un acheteur en onboarding ne peut pas soumettre son dossier
        # KYC tant qu'il ne compte pas au moins un validateur_1 ET un validateur_2 distincts.
        roles_presents = {
            u.role
            for u in db.query(Utilisateur).filter(Utilisateur.entreprise_id == entreprise.id).all()
        }
        manquants = {RoleUtilisateur.VALIDATEUR_1, RoleUtilisateur.VALIDATEUR_2} - roles_presents
        if manquants:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Un second validateur doit être ajouté avant de soumettre le dossier KYC",
            )

    if entreprise.forme_juridique is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La forme juridique de l'entreprise doit etre renseignee avant de televerser un document KYC",
        )

    dossier = _UPLOAD_ROOT / str(entreprise_id)
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / fichier.filename
    contenu = await fichier.read()
    chemin.write_bytes(contenu)

    entreprise.kyc_document_url = f"/uploads/kyc/{entreprise_id}/{fichier.filename}"
    entreprise.statut_kyc = StatutKyc.EN_ATTENTE
    entreprise.motif_rejet_kyc = None
    enregistrer_audit(
        db,
        entite_type="Entreprise",
        entite_id=entreprise.id,
        action="televersement_kyc",
        utilisateur_id=current_user.id,
        valeur_apres={"kyc_document_url": entreprise.kyc_document_url},
    )
    db.commit()
    return KycUploadResponse(kyc_document_url=entreprise.kyc_document_url, statut_kyc=entreprise.statut_kyc)


@router.patch("/{entreprise_id}/kyc", response_model=EntrepriseOut)
def modifier_statut_kyc(
    entreprise_id: uuid.UUID,
    payload: KycStatutUpdate,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(require_role(_ROLES_ADMIN)),
):
    entreprise = _get_entreprise_or_404(db, entreprise_id)

    if payload.statut_kyc == StatutKyc.VALIDE:
        if entreprise.forme_juridique is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La forme juridique de l'entreprise doit etre renseignee avant de valider le KYC",
            )
        manquants = _documents_manquants_kyc(entreprise)
        if manquants:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Impossible de valider le KYC, document(s) manquant(s) : {', '.join(manquants)}",
            )

    avant = {"statut_kyc": entreprise.statut_kyc.value, "motif_rejet_kyc": entreprise.motif_rejet_kyc}
    entreprise.statut_kyc = payload.statut_kyc
    entreprise.motif_rejet_kyc = payload.motif_rejet if payload.statut_kyc == StatutKyc.REJETE else None

    factures_debloquees = 0
    if payload.statut_kyc == StatutKyc.VALIDE and entreprise.statut_fiche == StatutFiche.PRE_INSCRITE:
        # Double bascule (doc §3.0quater/§3.5.2) : la validation KYC admin d'un acheteur
        # pre-inscrit active sa fiche ET debloque automatiquement toute facture qui
        # attendait cette activation pour entrer dans le circuit de validation standard.
        entreprise.statut_fiche = StatutFiche.ACTIVE
        factures_en_attente = (
            db.query(Facture)
            .filter(
                Facture.donneur_ordre_id == entreprise.id,
                Facture.statut == StatutFacture.EN_ATTENTE_KYC_ACHETEUR,
            )
            .all()
        )
        for f in factures_en_attente:
            f.statut = StatutFacture.EMISE
        factures_debloquees = len(factures_en_attente)

    enregistrer_audit(
        db,
        entite_type="Entreprise",
        entite_id=entreprise.id,
        action="maj_statut_kyc",
        utilisateur_id=current_user.id,
        valeur_avant=avant,
        valeur_apres={
            "statut_kyc": entreprise.statut_kyc.value,
            "motif_rejet_kyc": entreprise.motif_rejet_kyc,
            "statut_fiche": entreprise.statut_fiche.value,
            "factures_debloquees": factures_debloquees,
        },
    )
    db.commit()
    db.refresh(entreprise)
    return entreprise
