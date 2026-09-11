import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import StatutTicket


class TicketSupport(Base):
    __tablename__ = "tickets_support"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entreprise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entreprises.id", ondelete="CASCADE"), nullable=False
    )
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("utilisateurs.id", ondelete="RESTRICT"), nullable=False
    )
    sujet: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
    statut: Mapped[StatutTicket] = mapped_column(
        Enum(StatutTicket, name="statut_ticket"), nullable=False, default=StatutTicket.OUVERT
    )
    priorite: Mapped[str] = mapped_column(String(20), nullable=False, default="normale")
    date_creation: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    date_resolution: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    entreprise: Mapped["Entreprise"] = relationship(foreign_keys=[entreprise_id])
    utilisateur: Mapped["Utilisateur"] = relationship(foreign_keys=[utilisateur_id])
