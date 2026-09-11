import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import TypeLimite


class LimiteCredit(Base):
    __tablename__ = "limites_credit"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partenaire_financier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entreprises.id", ondelete="CASCADE"), nullable=False
    )
    entreprise_cible_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entreprises.id", ondelete="CASCADE"), nullable=False
    )
    type_limite: Mapped[TypeLimite] = mapped_column(Enum(TypeLimite, name="type_limite"), nullable=False)
    montant_plafond: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    montant_utilise: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    partenaire_financier: Mapped["Entreprise"] = relationship(foreign_keys=[partenaire_financier_id])
    entreprise_cible: Mapped["Entreprise"] = relationship(foreign_keys=[entreprise_cible_id])
