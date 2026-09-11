import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JournalAudit(Base):
    """Append-only audit trail. No UPDATE/DELETE endpoint is ever exposed on this table."""

    __tablename__ = "journal_audit"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entite_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entite_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    utilisateur_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True
    )
    horodatage: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    valeur_avant: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    valeur_apres: Mapped[dict] = mapped_column(JSON, nullable=False)
