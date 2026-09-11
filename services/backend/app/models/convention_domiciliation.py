import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import StatutCompteDedie


class CompteDedie(Base):
    """Compte bancaire dedie ouvert pour une relation PME<->donneur d'ordre, sur lequel les
    paiements du donneur d'ordre sont domicilies (doc §3.3ter). Cycle de vie manuel : les
    statuts sont mis a jour par l'admin, pas de veritable ouverture bancaire automatisee."""

    __tablename__ = "comptes_dedies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    relation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("relations_pme_donneur_ordre.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    numero_compte: Mapped[str] = mapped_column(String(64), nullable=False)
    banque_teneur: Mapped[str] = mapped_column(String(255), nullable=False)
    statut: Mapped[StatutCompteDedie] = mapped_column(
        Enum(StatutCompteDedie, name="statut_compte_dedie"), nullable=False, default=StatutCompteDedie.EN_OUVERTURE
    )
    date_ouverture: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_creation: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    relation: Mapped["RelationPmeDonneurOrdre"] = relationship()


class ConventionDomiciliation(Base):
    """Convention tripartite (PME, donneur d'ordre, partenaire) organisant la domiciliation
    des paiements sur le CompteDedie de la relation (doc §3.3ter). Signature manuelle :
    chaque partie est cochee par l'admin au fur et a mesure, pas de signature electronique
    reelle pour ce MVP."""

    __tablename__ = "conventions_domiciliation"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    relation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("relations_pme_donneur_ordre.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    compte_dedie_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comptes_dedies.id", ondelete="SET NULL"), nullable=True
    )
    signature_pme: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    signature_donneur_ordre: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    signature_partenaire: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    date_creation: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    relation: Mapped["RelationPmeDonneurOrdre"] = relationship()
    compte_dedie: Mapped["CompteDedie | None"] = relationship()
