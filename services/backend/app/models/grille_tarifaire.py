import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import TypePartenaire


class GrilleTarifaire(Base):
    """Bareme degressif selon la duree (doc §6.1bis/6.2) : le taux total interpole
    lineairement entre taux_total_minimum (a duree_minimum_jours) et taux_total_maximum
    (a duree_maximum_jours), puis se repartit entre Cedra et le partenaire selon
    proportion_cedra/proportion_partenaire. Une seule grille reste conforme aux plafonds
    TAEG banque (14%) et IMF (24%) sur toute la fenetre 60-90 jours."""

    __tablename__ = "grilles_tarifaires"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    taux_total_minimum: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    taux_total_maximum: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    proportion_cedra: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    proportion_partenaire: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    plafond_montant: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    duree_minimum_jours: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    duree_maximum_jours: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    taux_avance: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0.80"))
    type_partenaire: Mapped[TypePartenaire] = mapped_column(
        Enum(TypePartenaire, name="type_partenaire"), nullable=False, default=TypePartenaire.BANQUE
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    date_debut_validite: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin_validite: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
