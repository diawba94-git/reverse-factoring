import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Invitation(Base):
    """Tracks a pending self-service invitation. The invited Utilisateur row already
    exists (compte_actif=False, unusable placeholder password) the moment the invite is
    sent; accepting the invitation via the token just sets a real password and activates
    the account (see POST /auth/accepter-invitation/{token})."""

    __tablename__ = "invitations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("utilisateurs.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    invite_par_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True
    )
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    utilisateur: Mapped["Utilisateur"] = relationship(foreign_keys=[utilisateur_id])
    invite_par: Mapped["Utilisateur"] = relationship(foreign_keys=[invite_par_id])
