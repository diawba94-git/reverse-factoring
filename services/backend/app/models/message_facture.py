import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MessageFacture(Base):
    __tablename__ = "messages_facture"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("factures.id", ondelete="CASCADE"), nullable=False
    )
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("utilisateurs.id", ondelete="RESTRICT"), nullable=False
    )
    contenu: Mapped[str] = mapped_column(String(4000), nullable=False)
    date_envoi: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    lu: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    facture: Mapped["Facture"] = relationship(back_populates="messages")
    utilisateur: Mapped["Utilisateur"] = relationship()
