import uuid

from pydantic import BaseModel

from app.models.enums import StatutFiche, StatutKyc


class DoublonEntrepriseOut(BaseModel):
    id: uuid.UUID
    raison_sociale: str
    statut_fiche: StatutFiche
    statut_kyc: StatutKyc
    contact_telephone: str
    cree_par: str | None
    nombre_factures: int


class DoublonCandidatOut(BaseModel):
    # `conserver` est une suggestion (la fiche ACTIVE, ou la plus ancienne a defaut) : l'admin
    # peut inverser le sens dans POST /admin/doublons/fusionner.
    conserver: DoublonEntrepriseOut
    fusionner: DoublonEntrepriseOut
    score_similarite: float
    critere: str


class FusionDoublonRequest(BaseModel):
    conserver_id: uuid.UUID
    fusionner_id: uuid.UUID


class FusionDoublonResultOut(BaseModel):
    conserver_id: uuid.UUID
    fusionner_id: uuid.UUID
    factures_reassignees: int
    utilisateurs_reassignes: int
