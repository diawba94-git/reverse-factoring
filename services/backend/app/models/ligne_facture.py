import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LigneFacture(Base):
    __tablename__ = "lignes_facture"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("factures.id", ondelete="CASCADE"), nullable=False
    )
    ordre: Mapped[int] = mapped_column(Integer, nullable=False)
    designation: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantite: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    prix_unitaire: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    # Recalcule cote service (app.services.facture_native) a chaque ecriture plutot
    # qu'en colonne generee par la base : reste portable et lisible depuis l'ORM sans
    # dependre d'une expression SQL specifique a Postgres.
    montant_ligne: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    facture: Mapped["Facture"] = relationship(back_populates="lignes")
