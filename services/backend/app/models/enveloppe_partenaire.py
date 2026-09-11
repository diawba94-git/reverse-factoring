import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EnveloppePartenaire(Base):
    """Capital qu'un partenaire financier s'engage a financer sur Cedra (doc §3.3ter) —
    c'est cette enveloppe, pas une limite abstraite, qui borne reellement ce qu'il peut
    financer. montant_engage/montant_disponible sont calcules a la volee (jamais stockes)
    a partir des Avance en statut avance_versee non encore soldees."""

    __tablename__ = "enveloppes_partenaire"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partenaire_financier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entreprises.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    montant_total_alloue: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=Decimal("0"))
    date_maj: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    partenaire_financier: Mapped["Entreprise"] = relationship()
