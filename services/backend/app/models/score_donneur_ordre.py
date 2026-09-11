import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ScoreDonneurOrdre(Base):
    __tablename__ = "scores_donneur_ordre"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entreprise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entreprises.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    facteurs_positifs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    facteurs_negatifs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    modele_version: Mapped[str] = mapped_column(String(50), nullable=False)
    date_calcul: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    calculee_par: Mapped[str] = mapped_column(String(100), nullable=False)

    entreprise: Mapped["Entreprise"] = relationship(foreign_keys=[entreprise_id])
