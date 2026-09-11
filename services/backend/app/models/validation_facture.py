import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import RoleValidateur


class ValidationFacture(Base):
    __tablename__ = "validations_facture"
    __table_args__ = (
        UniqueConstraint("facture_id", "role_validateur", name="uq_validation_facture_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("factures.id", ondelete="CASCADE"), nullable=False
    )
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("utilisateurs.id", ondelete="RESTRICT"), nullable=False
    )
    role_validateur: Mapped[RoleValidateur] = mapped_column(
        Enum(RoleValidateur, name="role_validateur", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    date_validation: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    commentaire: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    facture: Mapped["Facture"] = relationship(back_populates="validations")
    utilisateur: Mapped["Utilisateur"] = relationship()
