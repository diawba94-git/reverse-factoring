import uuid
from datetime import date, datetime, timezone

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.entreprise import Entreprise
from app.models.enums import RoleUtilisateur, StatutKyc
from app.models.invitation import Invitation
from app.models.utilisateur import RefreshToken, Utilisateur
from app.schemas.auth import (
    AccepterInvitationRequest,
    LoginRequest,
    LoginResponse,
    MeEntrepriseOut,
    MeResponse,
    MfaSetupResponse,
    MfaVerifyRequest,
    RefreshRequest,
    RegisterEntrepriseRequest,
    RegisterRequest,
    RejoindreEntrepriseRequest,
    TokenResponse,
)
from app.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.services.audit import enregistrer_audit
from app.services.relations import affecter_validateur, obtenir_ou_creer_relation
from app.services.roles import ROLE_PAR_DEFAUT_PAR_TYPE, ROLES_AUTORISES_PAR_TYPE, ROLES_VALIDATEURS

router = APIRouter(prefix="/auth", tags=["auth"])

# `admin` est le seul role jamais attribuable par /auth/register ou par invitation : il
# n'existe qu'en base (bootstrap via scripts/seed_admin.py) ou via /utilisateurs (deja
# reserve aux admins).
_ROLES_INTERNES = {RoleUtilisateur.ADMIN}


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cree un utilisateur sur une entreprise EXISTANTE",
    description=(
        "Usage interne/admin : rattache un nouvel utilisateur a une entreprise deja "
        "creee (entreprise_id fourni). Pour l'inscription en libre-service qui cree "
        "l'entreprise ET son premier utilisateur en une seule operation, voir "
        "POST /auth/register-entreprise. Le role demande est verifie contre le type de "
        "l'entreprise cible (voir app.services.roles.ROLES_AUTORISES_PAR_TYPE) ; `admin` "
        "n'est jamais attribuable ici."
    ),
)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    if payload.role in _ROLES_INTERNES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Les roles internes ne peuvent etre crees que par un administrateur via /utilisateurs",
        )

    entreprise = db.get(Entreprise, payload.entreprise_id)
    if entreprise is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entreprise introuvable")

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
    if payload.email and db.query(Utilisateur).filter(func.lower(Utilisateur.email) == payload.email.lower()).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cet email est deja utilise")

    utilisateur = Utilisateur(
        entreprise_id=payload.entreprise_id,
        role=payload.role,
        nom=payload.nom,
        telephone=payload.telephone,
        email=payload.email,
        mot_de_passe_hash=hash_password(payload.mot_de_passe),
    )
    db.add(utilisateur)
    db.flush()
    enregistrer_audit(
        db,
        entite_type="Utilisateur",
        entite_id=utilisateur.id,
        action="creation",
        utilisateur_id=utilisateur.id,
        valeur_apres={"telephone": utilisateur.telephone, "role": utilisateur.role.value},
    )
    db.commit()

    return _emettre_tokens(db, utilisateur, request)


@router.post("/register-entreprise", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_entreprise(payload: RegisterEntrepriseRequest, request: Request, db: Session = Depends(get_db)):
    """Inscription en libre-service (ecran 'Creer un compte') : cree l'Entreprise et son
    premier Utilisateur en une seule operation. statut_kyc demarre a 'en_attente' ; aucune
    connexion automatique n'est requise cote frontend (voir PendingValidation)."""
    if db.query(Utilisateur).filter(Utilisateur.telephone == payload.telephone).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce numero de telephone est deja utilise")
    if db.query(Utilisateur).filter(func.lower(Utilisateur.email) == payload.email.lower()).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cet email est deja utilise")

    if db.query(Entreprise).filter(Entreprise.ninea == payload.ninea).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Une entreprise avec ce NINEA existe deja")

    entreprise = Entreprise(
        type=payload.type,
        raison_sociale=payload.raison_sociale,
        ninea=payload.ninea,
        forme_juridique=payload.forme_juridique,
        rccm=payload.rccm,
        statut_kyc=StatutKyc.EN_ATTENTE,
        secteur_activite=payload.secteur_activite,
        date_creation=date.today(),
        contact_telephone=payload.telephone,
        contact_email=payload.email,
        adresse=payload.adresse,
    )
    db.add(entreprise)
    db.flush()

    utilisateur = Utilisateur(
        entreprise_id=entreprise.id,
        role=ROLE_PAR_DEFAUT_PAR_TYPE[payload.type],
        nom=payload.nom,
        telephone=payload.telephone,
        email=payload.email,
        mot_de_passe_hash=hash_password(payload.mot_de_passe),
    )
    db.add(utilisateur)
    db.flush()

    enregistrer_audit(
        db,
        entite_type="Entreprise",
        entite_id=entreprise.id,
        action="creation_inscription",
        utilisateur_id=utilisateur.id,
        valeur_apres={"raison_sociale": entreprise.raison_sociale, "type": entreprise.type.value},
    )
    enregistrer_audit(
        db,
        entite_type="Utilisateur",
        entite_id=utilisateur.id,
        action="creation_inscription",
        utilisateur_id=utilisateur.id,
        valeur_apres={"telephone": utilisateur.telephone, "role": utilisateur.role.value},
    )
    db.commit()

    return _emettre_tokens(db, utilisateur, request)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    identifiant = payload.identifiant.strip()
    utilisateur = (
        db.query(Utilisateur)
        .filter(or_(Utilisateur.telephone == identifiant, func.lower(Utilisateur.email) == identifiant.lower()))
        .first()
    )
    if utilisateur is None or not verify_password(payload.mot_de_passe, utilisateur.mot_de_passe_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides")

    if not utilisateur.compte_actif:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte desactive")

    if utilisateur.mfa_actif:
        if not payload.code_mfa:
            return LoginResponse(mfa_required=True)
        totp = pyotp.TOTP(utilisateur.mfa_secret)
        if not totp.verify(payload.code_mfa, valid_window=1):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Code MFA invalide")

    utilisateur.derniere_connexion = datetime.now(timezone.utc)
    db.commit()

    tokens = _emettre_tokens(db, utilisateur, request)
    return LoginResponse(mfa_required=False, access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    try:
        claims = decode_token(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    if claims.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide : type incorrect")

    jti = claims.get("jti")
    stored = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if stored is None or stored.revoked or stored.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalide ou revoque")

    utilisateur = db.get(Utilisateur, uuid.UUID(claims["sub"]))
    if utilisateur is None or not utilisateur.compte_actif:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur inconnu ou compte desactive")

    stored.revoked = True
    return _emettre_tokens(db, utilisateur, request)


@router.post(
    "/accepter-invitation/{token}",
    response_model=TokenResponse,
    summary="Active un compte invite et definit son mot de passe",
    description=(
        "A appeler avec le token recu via une invitation (voir POST "
        "/entreprises/{entreprise_id}/inviter). Definit le mot de passe de l'invite, "
        "active son compte (compte_actif=true) et retourne directement une session : "
        "l'entreprise de l'invite est necessairement deja validee cote KYC, puisque seule "
        "une entreprise validee peut envoyer des invitations."
    ),
)
def accepter_invitation(
    token: str, payload: AccepterInvitationRequest, request: Request, db: Session = Depends(get_db)
):
    invitation = db.query(Invitation).filter(Invitation.token == token).first()
    if invitation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation introuvable")
    if invitation.accepted_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cette invitation a deja ete acceptee")
    if invitation.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cette invitation a expire")

    utilisateur = invitation.utilisateur
    utilisateur.mot_de_passe_hash = hash_password(payload.mot_de_passe)
    utilisateur.compte_actif = True
    invitation.accepted_at = datetime.now(timezone.utc)

    enregistrer_audit(
        db,
        entite_type="Utilisateur",
        entite_id=utilisateur.id,
        action="acceptation_invitation",
        utilisateur_id=utilisateur.id,
        valeur_apres={"telephone": utilisateur.telephone},
    )
    db.commit()

    return _emettre_tokens(db, utilisateur, request)


@router.post(
    "/rejoindre-entreprise/{token}",
    response_model=TokenResponse,
    summary="Rejoint une fiche acheteur minimale comme premier validateur (validateur_1)",
    description=(
        "A appeler avec le jeton recu par le contact designe lors de la creation d'une "
        "fiche acheteur minimale (voir POST /entreprises/fiche-minimale, doc §3.0quater "
        "cas B puis §3.0quinquies.1). Cree le compte validateur_1, l'affecte a la relation "
        "PME<->donneur d'ordre a l'origine de l'invitation, et retourne une session active — "
        "contrairement a /auth/accepter-invitation, ce compte n'existait pas encore."
    ),
)
def rejoindre_entreprise(
    token: str, payload: RejoindreEntrepriseRequest, request: Request, db: Session = Depends(get_db)
):
    entreprise = db.query(Entreprise).filter(Entreprise.token_invitation_initiale == token).first()
    if entreprise is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lien d'invitation introuvable ou déjà utilisé")

    if db.query(Utilisateur).filter(Utilisateur.telephone == payload.telephone).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce numero de telephone est deja utilise")
    if entreprise.contact_invitation_email and db.query(Utilisateur).filter(
        func.lower(Utilisateur.email) == entreprise.contact_invitation_email.lower()
    ).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cet email est deja utilise")

    utilisateur = Utilisateur(
        entreprise_id=entreprise.id,
        role=RoleUtilisateur.VALIDATEUR_1,
        nom=payload.nom,
        telephone=payload.telephone,
        email=entreprise.contact_invitation_email,
        mot_de_passe_hash=hash_password(payload.mot_de_passe),
        compte_actif=True,
    )
    db.add(utilisateur)
    db.flush()

    entreprise.token_invitation_initiale = None
    if entreprise.cree_par_entreprise_id is not None:
        relation = obtenir_ou_creer_relation(
            db, pme_id=entreprise.cree_par_entreprise_id, donneur_ordre_id=entreprise.id
        )
        affecter_validateur(db, relation_id=relation.id, utilisateur_id=utilisateur.id)

    enregistrer_audit(
        db,
        entite_type="Utilisateur",
        entite_id=utilisateur.id,
        action="rejoint_entreprise",
        utilisateur_id=utilisateur.id,
        valeur_apres={"telephone": utilisateur.telephone, "entreprise_id": str(entreprise.id)},
    )
    db.commit()

    return _emettre_tokens(db, utilisateur, request)


@router.get("/me", response_model=MeResponse)
def me(current_user: Utilisateur = Depends(get_current_user)):
    entreprise = current_user.entreprise
    return MeResponse(
        id=current_user.id,
        telephone=current_user.telephone,
        email=current_user.email,
        nom=current_user.nom,
        role=current_user.role,
        mfa_actif=current_user.mfa_actif,
        entreprise=MeEntrepriseOut(
            id=entreprise.id,
            type=entreprise.type,
            raison_sociale=entreprise.raison_sociale,
            statut_kyc=entreprise.statut_kyc,
            kyc_document_url=entreprise.kyc_document_url,
            motif_rejet_kyc=entreprise.motif_rejet_kyc,
        ),
    )


def _emettre_tokens(db: Session, utilisateur: Utilisateur, request: Request | None = None) -> TokenResponse:
    access_token = create_access_token(str(utilisateur.id), utilisateur.role.value)
    refresh_token, jti, expires_at = create_refresh_token(str(utilisateur.id))
    db.add(
        RefreshToken(
            utilisateur_id=utilisateur.id,
            jti=jti,
            expires_at=expires_at,
            user_agent=request.headers.get("user-agent") if request else None,
            ip_address=request.client.host if request and request.client else None,
        )
    )
    db.commit()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


_ROLES_MFA_ELIGIBLES = ROLES_VALIDATEURS | {RoleUtilisateur.AGENT_FINANCIER}


@router.post("/mfa/setup", response_model=MfaSetupResponse)
def mfa_setup(db: Session = Depends(get_db), current_user: Utilisateur = Depends(get_current_user)):
    if current_user.role not in _ROLES_MFA_ELIGIBLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Le MFA est reserve aux validateurs (validateur_1, validateur_2) et agents financiers",
        )

    secret = pyotp.random_base32()
    current_user.mfa_secret = secret
    current_user.mfa_actif = False
    db.commit()

    otpauth_uri = pyotp.TOTP(secret).provisioning_uri(
        name=current_user.telephone, issuer_name=settings.MFA_ISSUER_NAME
    )
    return MfaSetupResponse(secret=secret, otpauth_uri=otpauth_uri)


@router.post("/mfa/verify", status_code=status.HTTP_204_NO_CONTENT)
def mfa_verify(
    payload: MfaVerifyRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    if not current_user.mfa_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Aucune configuration MFA en attente")

    totp = pyotp.TOTP(current_user.mfa_secret)
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Code MFA invalide")

    current_user.mfa_actif = True
    db.commit()
