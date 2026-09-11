import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, model_validator

from app.models.enums import FormeJuridique, StatutFiche, StatutKyc, TypeEntreprise
from app.schemas.common import ORMBase
from app.services.kyc import rccm_est_obligatoire


class EntrepriseCreate(BaseModel):
    type: TypeEntreprise
    raison_sociale: str
    ninea: str
    forme_juridique: FormeJuridique
    rccm: str | None = None
    secteur_activite: str
    chiffre_affaires: Decimal | None = None
    date_creation: date
    contact_telephone: str
    contact_email: str
    adresse: str

    @model_validator(mode="after")
    def _valider_rccm(self) -> "EntrepriseCreate":
        if rccm_est_obligatoire(self.forme_juridique) and not self.rccm:
            raise ValueError(f"Le RCCM est obligatoire pour la forme juridique '{self.forme_juridique.value}'")
        return self


class EntrepriseUpdate(BaseModel):
    raison_sociale: str | None = None
    forme_juridique: FormeJuridique | None = None
    rccm: str | None = None
    secteur_activite: str | None = None
    chiffre_affaires: Decimal | None = None
    contact_telephone: str | None = None
    contact_email: str | None = None
    adresse: str | None = None


class EntrepriseOut(ORMBase):
    id: uuid.UUID
    type: TypeEntreprise
    raison_sociale: str
    ninea: str | None
    forme_juridique: FormeJuridique | None
    rccm: str | None
    statut_kyc: StatutKyc
    secteur_activite: str | None
    chiffre_affaires: Decimal | None
    date_creation: date | None
    contact_telephone: str | None
    contact_email: str | None
    adresse: str | None
    kyc_document_url: str | None
    motif_rejet_kyc: str | None
    statut_fiche: StatutFiche
    cree_par_entreprise_id: uuid.UUID | None
    contact_invitation_nom: str | None
    contact_invitation_email: str | None
    date_invitation_envoyee: datetime | None
    actif: bool
    created_at: datetime


class FicheMinimaleOut(EntrepriseOut):
    # Stub, comme le token de POST /entreprises/{id}/inviter : aucun canal email n'est
    # encore branche, donc le jeton est retourne ici (une seule fois) pour rester testable
    # de bout en bout, plutot que d'etre uniquement "envoye" au contact invite.
    token_invitation: str | None = None


class FicheMinimaleCreate(BaseModel):
    """Fiche acheteur minimale (doc §3.0quater, cas B) : une PME qui adresse sa premiere
    facture a un acheteur pas encore present sur Cedra ne saisit que son nom et un contact —
    le reste (NINEA, adresse...) sera complete par l'acheteur lui-meme a son onboarding."""

    raison_sociale: str
    contact_invitation_nom: str
    contact_invitation_email: str


class KycStatutUpdate(BaseModel):
    statut_kyc: StatutKyc
    motif_rejet: str | None = None


class KycUploadResponse(BaseModel):
    kyc_document_url: str
    statut_kyc: StatutKyc
