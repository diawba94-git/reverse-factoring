import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import StatutRapprochement


class Remboursement(Base):
    __tablename__ = "remboursements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    avance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("avances.id", ondelete="RESTRICT"), nullable=False
    )
    montant_recu: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    date_reception: Mapped[date] = mapped_column(Date, nullable=False)
    source_entreprise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entreprises.id", ondelete="RESTRICT"), nullable=False
    )
    statut_rapprochement: Mapped[StatutRapprochement] = mapped_column(
        Enum(StatutRapprochement, name="statut_rapprochement"), nullable=False, default=StatutRapprochement.EN_ATTENTE
    )
    declenche_versement_solde: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    avance: Mapped["Avance"] = relationship(back_populates="remboursements")
    source_entreprise: Mapped["Entreprise"] = relationship(foreign_keys=[source_entreprise_id])
