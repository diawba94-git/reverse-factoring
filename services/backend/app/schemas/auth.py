import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.enums import FormeJuridique, RoleUtilisateur, StatutKyc, TypeEntreprise
from app.services.kyc import rccm_est_obligatoire

_NINEA_PATTERN = re.compile(r"^\d{9}([0-9A-Za-z]{3})?$")


class RegisterRequest(BaseModel):
    entreprise_id: uuid.UUID
    role: RoleUtilisateur
    nom: str = Field(min_length=2, max_length=255)
    telephone: str = Field(min_length=6, max_length=30)
    email: str | None = None
    mot_de_passe: str = Field(min_length=8)


class RegisterEntrepriseRequest(BaseModel):
    """Inscription en libre-service : cree l'Entreprise et son premier Utilisateur en une
    seule operation atomique. Le type d'entreprise choisi determine le role cree :
    PME -> membre_pme, GRANDE_ENTREPRISE -> validateur_1 (le premier arrivant ; il pourra
    ensuite inviter un collegue validateur_2, la double validation etant obligatoire pour
    toute facture), PARTENAIRE_FINANCIER -> agent_financier."""

    type: TypeEntreprise
    raison_sociale: str = Field(min_length=2, max_length=255)
    ninea: str
    forme_juridique: FormeJuridique
    rccm: str | None = None
    secteur_activite: str = Field(min_length=2, max_length=255)
    adresse: str = Field(min_length=5, max_length=500)
    nom: str = Field(min_length=2, max_length=255)
    telephone: str = Field(min_length=6, max_length=30)
    email: EmailStr
    mot_de_passe: str = Field(min_length=8)

    @field_validator("ninea")
    @classmethod
    def _valider_ninea(cls, value: str) -> str:
        value = value.strip().upper()
        if not _NINEA_PATTERN.match(value):
            raise ValueError(
                "Format NINEA invalide (attendu : 9 chiffres, suivis eventuellement "
                "d'un code regime de 3 caracteres, ex. 005912345 ou 0059123451A1)"
            )
        return value

    @model_validator(mode="after")
    def _valider_rccm(self) -> "RegisterEntrepriseRequest":
        if rccm_est_obligatoire(self.forme_juridique) and not self.rccm:
            raise ValueError(f"Le RCCM est obligatoire pour la forme juridique '{self.forme_juridique.value}'")
        return self


class LoginRequest(BaseModel):
    telephone: str
    mot_de_passe: str
    code_mfa: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    """Superset of TokenResponse: when the account has MFA enabled and no code_mfa was
    sent, mfa_required=True is returned (HTTP 200, not an error) with the token fields
    left empty, so the client can show the OTP step. Genuinely wrong credentials/codes
    still raise 401/403 as errors."""

    mfa_required: bool = False
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class MfaSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str


class MfaVerifyRequest(BaseModel):
    code: str


class MeEntrepriseOut(BaseModel):
    id: uuid.UUID
    type: TypeEntreprise
    raison_sociale: str
    statut_kyc: StatutKyc
    kyc_document_url: str | None
    motif_rejet_kyc: str | None


class MeResponse(BaseModel):
    id: uuid.UUID
    telephone: str
    email: str | None
    nom: str | None
    role: RoleUtilisateur
    mfa_actif: bool
    entreprise: MeEntrepriseOut


class InviterRequest(BaseModel):
    """Corps de POST /entreprises/{entreprise_id}/inviter. Le role demande est valide
    server-side contre le type de l'entreprise de l'appelant (voir
    app.services.roles.ROLES_AUTORISES_PAR_TYPE) : une PME ne peut inviter qu'en
    membre_pme, une GRANDE_ENTREPRISE qu'en validateur_1 ou validateur_2, un
    PARTENAIRE_FINANCIER qu'en agent_financier. `admin` n'est jamais un choix valide ici."""

    telephone: str = Field(min_length=6, max_length=30)
    email: EmailStr
    nom: str = Field(min_length=2, max_length=255)
    role: RoleUtilisateur


class InvitationOut(BaseModel):
    id: uuid.UUID
    utilisateur_id: uuid.UUID
    entreprise_id: uuid.UUID
    telephone: str
    email: str
    nom: str
    role: RoleUtilisateur
    expires_at: datetime
    # NOTE : aucun envoi email/SMS n'est encore branche (comme le webhook Wave, c'est un
    # stub pour cette phase) — le token est donc renvoye directement dans la reponse pour
    # rester testable de bout en bout. Dans une integration reelle, il ne transiterait que
    # par le canal email/SMS et ne serait jamais renvoye dans la reponse API.
    token: str


class AccepterInvitationRequest(BaseModel):
    mot_de_passe: str = Field(min_length=8)


class RejoindreEntrepriseRequest(BaseModel):
    """Corps de POST /auth/rejoindre-entreprise/{token} : le contact designe par une PME
    a la creation d'une fiche acheteur minimale (voir POST /entreprises/fiche-minimale)
    rejoint cette fiche comme premier validateur (validateur_1) — doc §3.0quinquies.1."""

    nom: str = Field(min_length=2, max_length=255)
    telephone: str = Field(min_length=6, max_length=30)
    mot_de_passe: str = Field(min_length=8)
