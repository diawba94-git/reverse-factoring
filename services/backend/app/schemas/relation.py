import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import StatutCompteDedie, StatutRelation


class RelationOut(BaseModel):
    id: uuid.UUID
    pme_id: uuid.UUID
    pme_raison_sociale: str
    donneur_ordre_id: uuid.UUID
    donneur_ordre_raison_sociale: str
    statut: StatutRelation
    factures_pilote_max: int
    factures_pilote_utilisees: int
    date_debut_relation: datetime
    compte_dedie_statut: StatutCompteDedie | None = None
    nombre_signatures: int = 0


class RelationResumeOut(BaseModel):
    pilote: int
    convention_signee: int


class RelationStatutUpdate(BaseModel):
    statut: StatutRelation


class ConventionSignatureUpdate(BaseModel):
    signature_pme: bool | None = None
    signature_donneur_ordre: bool | None = None
    signature_partenaire: bool | None = None


class RelationChipOut(BaseModel):
    relation_id: uuid.UUID
    pme_id: uuid.UUID
    pme_raison_sociale: str


class ValidateurAvecRelationsOut(BaseModel):
    """Un validateur (validateur_1/2) de l'entreprise donneur d'ordre, avec les relations
    PME auxquelles il est affecte (doc §5.4). `relations_en_attente` ne liste, pour un
    validateur_2, que les relations de l'entreprise ayant deja un validateur_1 mais aucun
    validateur_2 — n'importe quel validateur_2 de l'entreprise peut les prendre en charge."""

    utilisateur_id: uuid.UUID
    nom: str | None
    role: str
    relations: list[RelationChipOut]
    relations_en_attente: list[RelationChipOut]
