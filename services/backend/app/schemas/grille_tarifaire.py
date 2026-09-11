import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import TypePartenaire
from app.schemas.common import ORMBase


class GrilleTarifaireCreate(BaseModel):
    nom: str
    taux_total_minimum: Decimal
    taux_total_maximum: Decimal
    proportion_cedra: Decimal
    proportion_partenaire: Decimal
    plafond_montant: Decimal | None = None
    duree_minimum_jours: int = 60
    duree_maximum_jours: int = 90
    taux_avance: Decimal = Decimal("0.80")
    type_partenaire: TypePartenaire = TypePartenaire.BANQUE
    active: bool = True
    date_debut_validite: date
    date_fin_validite: date | None = None


class GrilleTarifaireUpdate(BaseModel):
    nom: str | None = None
    taux_total_minimum: Decimal | None = None
    taux_total_maximum: Decimal | None = None
    proportion_cedra: Decimal | None = None
    proportion_partenaire: Decimal | None = None
    plafond_montant: Decimal | None = None
    duree_minimum_jours: int | None = None
    duree_maximum_jours: int | None = None
    taux_avance: Decimal | None = None
    type_partenaire: TypePartenaire | None = None
    active: bool | None = None
    date_fin_validite: date | None = None


class GrilleTarifaireOut(ORMBase):
    id: uuid.UUID
    nom: str
    taux_total_minimum: Decimal
    taux_total_maximum: Decimal
    proportion_cedra: Decimal
    proportion_partenaire: Decimal
    plafond_montant: Decimal | None
    duree_minimum_jours: int
    duree_maximum_jours: int
    taux_avance: Decimal
    type_partenaire: TypePartenaire
    active: bool
    date_debut_validite: date
    date_fin_validite: date | None
