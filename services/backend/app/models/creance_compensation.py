import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import StatutCreance


class CreanceCompensation(Base):
    """Reliquat du a une PME quand un avoir confirme depasse le solde restant d'une avance
    deja versee (architecture-mvp §3.0sexies) : deduit automatiquement de la prochaine
    avance versee a cette PME, sur n'importe quelle facture (voir
    app.services.gestion_avoirs.verifier_et_deduire_creances)."""

    __tablename__ = "creances_compensation"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entreprises.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    avoir_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("avoirs_facture.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    montant_du: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    montant_recouvre: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    statut: Mapped[StatutCreance] = mapped_column(
        Enum(StatutCreance, name="statut_creance"), nullable=False, default=StatutCreance.EN_ATTENTE
    )
    date_creation: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pme: Mapped["Entreprise"] = relationship(foreign_keys=[pme_id])
    avoir: Mapped["AvoirFacture"] = relationship(back_populates="creance")
