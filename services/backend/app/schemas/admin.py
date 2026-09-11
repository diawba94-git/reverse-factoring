import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import RoleUtilisateur
from app.schemas.utilisateur import UtilisateurOut


class AdminCreerUtilisateurRequest(BaseModel):
    nom: str = Field(min_length=2, max_length=255)
    telephone: str = Field(min_length=6, max_length=30)
    email: str | None = None
    role: RoleUtilisateur


class AdminUtilisateurCreeOut(UtilisateurOut):
    # Stub, comme le token de POST /entreprises/{id}/inviter : aucun canal SMS/email n'est
    # encore branche, donc le mot de passe temporaire est retourne ici (une seule fois) pour
    # rester testable de bout en bout, plutot que d'etre uniquement "envoye".
    mot_de_passe_temporaire: str


class AdminModifierUtilisateurRequest(BaseModel):
    role: RoleUtilisateur | None = None
    compte_actif: bool | None = None


class SessionOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    expires_at: datetime
    revoked: bool
    user_agent: str | None
    ip_address: str | None

    model_config = {"from_attributes": True}


class JournalAuditOut(BaseModel):
    id: uuid.UUID
    entite_type: str
    entite_id: uuid.UUID
    action: str
    utilisateur_id: uuid.UUID | None
    horodatage: datetime
    valeur_avant: dict | None
    valeur_apres: dict

    model_config = {"from_attributes": True}


class TransactionOut(BaseModel):
    facture_id: uuid.UUID
    numero_facture: str
    fournisseur: str
    acheteur: str
    montant: Decimal
    etape: str
    avance_id: uuid.UUID | None


class RemboursementSuperviseOut(BaseModel):
    id: uuid.UUID
    avance_id: uuid.UUID
    montant_recu: Decimal
    date_reception: date
    source_entreprise: str
    montant_attendu: Decimal
    ecart: Decimal
    statut_rapprochement: str

    model_config = {"from_attributes": True}


class RapportPeriodeOut(BaseModel):
    periode: str
    debut: date
    fin: date
    nombre_factures: int
    montant_total_factures: Decimal
    nombre_avances: int
    montant_total_avance_verse: Decimal
    montant_total_frais_plateforme: Decimal
    montant_total_rembourse: Decimal
