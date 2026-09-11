import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import CauseLitige, StatutFacture, StatutLitige


class LitigeDossier(Base):
    """Dossier de litige ouvert manuellement par l'admin sur une facture (chèque rejeté,
    contestation acheteur, écart de remboursement...). Le passage en litige reste une action
    manuelle au MVP (architecture-mvp-affacturage-inverse.md §5.5) — aucune automatisation."""

    __tablename__ = "litiges_dossiers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("factures.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    cause: Mapped[CauseLitige] = mapped_column(Enum(CauseLitige, name="cause_litige"), nullable=False)
    montant_en_jeu: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    statut: Mapped[StatutLitige] = mapped_column(
        Enum(StatutLitige, name="statut_litige"), nullable=False, default=StatutLitige.OUVERT
    )
    # Snapshot du statut de la facture juste avant bascule en `litige`, restaure a la
    # resolution du dossier (pas de regle generique pour "ou revenir", donc pas d'invention :
    # on revient exactement d'ou on vient).
    statut_facture_avant: Mapped[StatutFacture] = mapped_column(
        Enum(StatutFacture, name="statut_facture"), nullable=False
    )
    ouvert_par_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True
    )
    derniere_action: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    ouvert_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolu_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    facture: Mapped["Facture"] = relationship(foreign_keys=[facture_id])
    ouvert_par: Mapped["Utilisateur | None"] = relationship(foreign_keys=[ouvert_par_id])
