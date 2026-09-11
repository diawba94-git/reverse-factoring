import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import MethodeVersement, StatutAvance, StatutChequeGarantie, StatutKyc, StatutRelation
from app.schemas.common import ORMBase


class AvanceCreate(BaseModel):
    facture_id: uuid.UUID
    partenaire_financier_id: uuid.UUID
    methode_versement: MethodeVersement


class AvanceOut(ORMBase):
    id: uuid.UUID
    facture_id: uuid.UUID
    partenaire_financier_id: uuid.UUID
    grille_tarifaire_id: uuid.UUID
    montant_avance_initial: Decimal
    frais_total: Decimal
    montant_solde_du: Decimal
    part_partenaire: Decimal
    part_plateforme: Decimal
    taeg_annualise: Decimal
    date_versement_initial: datetime | None
    date_versement_solde: datetime | None
    statut: StatutAvance
    methode_versement: MethodeVersement
    garantie_detenue_avant_financement: bool
    created_at: datetime


class AvanceRejetRequest(BaseModel):
    commentaire: str


class ChequeResumeOut(BaseModel):
    numero_cheque: str
    banque_emettrice: str
    date_encaissement_prevue: date
    statut: StatutChequeGarantie


class DossierDecisionOut(BaseModel):
    """Vue consolidee pour l'ecran de decision du partenaire (doc §3.3quater.2) : rassemble
    tout ce qu'il doit verifier avant d'approuver/rejeter, deja calcule cote serveur."""

    avance: AvanceOut
    numero_facture: str | None
    montant_ttc: Decimal
    date_emission: date
    date_echeance: date
    duree_jours: int
    pme_raison_sociale: str
    pme_statut_kyc: StatutKyc
    donneur_ordre_raison_sociale: str
    donneur_ordre_statut_kyc: StatutKyc
    relation_statut: StatutRelation | None
    cheque: ChequeResumeOut | None
    enveloppe_disponible: Decimal | None
    enveloppe_totale: Decimal | None
    limite_acheteur_plafond: Decimal | None
    limite_acheteur_utilisee: Decimal | None
    historique_cycles_rembourses: int
    grille_taux_total: Decimal
    grille_plafond_montant: Decimal | None
