import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import StatutChequeGarantie


class ChequeGarantie(Base):
    """Cheque post-date remis par le donneur d'ordre a la PME, declare par cette derniere
    des la creation de la facture — bien avant qu'une Avance n'existe (doc §5.3bis). Une
    facture ne peut avoir qu'un seul cheque associe (facture_id UNIQUE)."""

    __tablename__ = "cheques_garantie"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("factures.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    declare_par_utilisateur_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True
    )
    numero_cheque: Mapped[str] = mapped_column(String(50), nullable=False)
    banque_emettrice: Mapped[str] = mapped_column(String(255), nullable=False)
    date_encaissement_prevue: Mapped[date] = mapped_column(Date, nullable=False)
    piece_jointe_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    statut: Mapped[StatutChequeGarantie] = mapped_column(
        Enum(StatutChequeGarantie, name="statut_cheque_garantie"),
        nullable=False,
        default=StatutChequeGarantie.DECLARE,
    )
    date_remise_partenaire: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_creation: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    facture: Mapped["Facture"] = relationship(back_populates="cheque_garantie")
