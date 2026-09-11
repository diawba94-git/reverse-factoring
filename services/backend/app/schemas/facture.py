import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import RoleValidateur, SourceCreationFacture, StatutFacture
from app.schemas.common import ORMBase


class PremiereValidationInfo(BaseModel):
    """Qui a valide en premier, tant que la facture attend la seconde validation
    (statut validation_complementaire_requise). Redevient absent une fois la facture
    pleinement validee (ou si elle n'a encore recu aucune validation)."""

    nom: str | None
    role_validateur: RoleValidateur
    date_validation: datetime


class LigneFactureOut(ORMBase):
    id: uuid.UUID
    ordre: int
    designation: str
    description: str | None
    quantite: Decimal
    prix_unitaire: Decimal
    montant_ligne: Decimal


class FactureOut(ORMBase):
    id: uuid.UUID
    numero_facture: str | None
    pme_id: uuid.UUID
    donneur_ordre_id: uuid.UUID
    montant_ht: Decimal
    taux_tva: Decimal
    montant_tva: Decimal
    montant_ttc: Decimal
    devise: str
    date_emission: date
    date_echeance: date
    duree_jours: int
    statut: StatutFacture
    piece_justificative_url: str
    description: str | None
    source_creation: SourceCreationFacture
    ninea_emetteur_extrait: str | None
    code_validation_dgid: str | None
    conformite_verifiee: bool
    motifs_rejet_conformite: list[str] | None
    date_derniere_maj: datetime
    created_at: datetime
    premiere_validation: PremiereValidationInfo | None = None
    historique_validations: list[PremiereValidationInfo] = []
    lignes: list[LigneFactureOut] = []


class LigneFactureCreate(BaseModel):
    designation: str = Field(min_length=1, max_length=255)
    description: str | None = None
    quantite: Decimal = Field(gt=0)
    prix_unitaire: Decimal = Field(gt=0)


class LigneFactureExtraiteOut(BaseModel):
    designation: str
    quantite: Decimal
    prix_unitaire: Decimal


class FactureExtractionOut(BaseModel):
    """Brouillon extrait d'un document existant (PDF ou photo/scan) pour pre-remplir le
    formulaire de creation de facture — jamais applique sans relecture par la PME."""

    via_ocr: bool
    numero_facture: str | None
    date_emission: date | None
    date_echeance: date | None
    taux_tva: Decimal | None
    montant_ht: Decimal | None
    montant_tva: Decimal | None
    montant_ttc: Decimal | None
    lignes: list[LigneFactureExtraiteOut]
    avertissements: list[str]


class FactureNativeCreate(BaseModel):
    donneur_ordre_id: uuid.UUID
    date_emission: date
    date_echeance: date
    taux_tva: Decimal = Decimal("0.18")
    notes: str | None = None
    lignes: list[LigneFactureCreate] = Field(min_length=1)
    pme_id: uuid.UUID | None = Field(default=None, description="Requis pour un admin ; ignore pour un membre_pme")

    @model_validator(mode="after")
    def _check_dates(self) -> "FactureNativeCreate":
        if self.date_echeance <= self.date_emission:
            raise ValueError("La date d'echeance doit etre posterieure a la date d'emission")
        return self


class LigneFactureUpdate(BaseModel):
    id: uuid.UUID | None = None
    designation: str = Field(min_length=1, max_length=255)
    description: str | None = None
    quantite: Decimal = Field(gt=0)
    prix_unitaire: Decimal = Field(gt=0)


class FactureLignesUpdateRequest(BaseModel):
    lignes: list[LigneFactureUpdate] = Field(min_length=1)


class FactureRejetRequest(BaseModel):
    commentaire: str


class FactureValiderRequest(BaseModel):
    """Valide la facture avec le role validateur_1 ou validateur_2 de l'appelant.
    La double validation est obligatoire pour 100% des factures, quel que soit le
    montant : une seule validation par role et par facture (voir role_validateur sur
    ValidationFacture)."""

    commentaire: str | None = None


class ImportLigneResultat(BaseModel):
    ligne: int
    succes: bool
    erreur: str | None = None
    facture_id: uuid.UUID | None = None
    conforme: bool | None = None
    motifs_rejet_conformite: list[str] | None = None


class FactureImportRapport(BaseModel):
    total_lignes: int
    succes: int
    echecs: int
    details: list[ImportLigneResultat]
