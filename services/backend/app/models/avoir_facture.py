import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import MotifAvoir, StatutAvoir


class AvoirFacture(Base):
    """Note de credit emise par une PME sur une facture deja emise (architecture-mvp
    §3.0sexies). N'a d'effet sur la Facture/l'Avance/une eventuelle CreanceCompensation
    qu'a la confirmation par l'acheteur (voir app.services.gestion_avoirs) — jamais a la
    simple creation, qui reste une proposition en attente."""

    __tablename__ = "avoirs_facture"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero_avoir: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Sequence continue, sans trou, par PME — independante de numero_facture (voir app.services.numerotation_avoir).",
    )
    facture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("factures.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    montant_ht: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    montant_tva: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    montant_ttc: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    motif: Mapped[MotifAvoir] = mapped_column(Enum(MotifAvoir, name="motif_avoir"), nullable=False)
    statut: Mapped[StatutAvoir] = mapped_column(
        Enum(StatutAvoir, name="statut_avoir"), nullable=False, default=StatutAvoir.EMIS
    )
    date_emission: Mapped[date] = mapped_column(Date, nullable=False)
    piece_justificative_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Bookkeeping pour la reversibilite exacte au rejet (meme principe que
    # LitigeDossier.statut_facture_avant) : ce que la confirmation a effectivement change,
    # pour pouvoir tout remettre a l'etat anterieur sans avoir a re-deviner l'effet applique.
    effet_applique: Mapped[str | None] = mapped_column(String(30), nullable=True)
    montant_deduit_solde: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    facture: Mapped["Facture"] = relationship(back_populates="avoirs")
    creance: Mapped["CreanceCompensation | None"] = relationship(back_populates="avoir", uselist=False)
