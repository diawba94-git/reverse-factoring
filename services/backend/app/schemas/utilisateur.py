import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import RoleUtilisateur
from app.schemas.common import ORMBase


class UtilisateurCreate(BaseModel):
    entreprise_id: uuid.UUID
    role: RoleUtilisateur
    nom: str = Field(min_length=2, max_length=255)
    telephone: str = Field(min_length=6, max_length=30)
    email: str | None = None
    mot_de_passe: str = Field(min_length=8)


class UtilisateurUpdate(BaseModel):
    nom: str | None = None
    email: str | None = None
    compte_actif: bool | None = None
    role: RoleUtilisateur | None = None


class UtilisateurOut(ORMBase):
    id: uuid.UUID
    entreprise_id: uuid.UUID
    role: RoleUtilisateur
    nom: str | None
    telephone: str
    email: str | None
    mfa_actif: bool
    derniere_connexion: datetime | None
    compte_actif: bool
    date_creation: datetime
