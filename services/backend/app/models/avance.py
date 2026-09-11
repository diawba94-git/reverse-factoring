import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import MethodeVersement, StatutAvance


class Avance(Base):
    __tablename__ = "avances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("factures.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    partenaire_financier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entreprises.id", ondelete="RESTRICT"), nullable=False
    )
    grille_tarifaire_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("grilles_tarifaires.id", ondelete="RESTRICT"), nullable=False
    )
    montant_avance_initial: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    frais_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    montant_solde_du: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    part_partenaire: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    part_plateforme: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    taeg_annualise: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    date_versement_initial: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_versement_solde: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    statut: Mapped[StatutAvance] = mapped_column(
        Enum(StatutAvance, name="statut_avance"), nullable=False, default=StatutAvance.EN_ATTENTE_VALIDATION
    )
    methode_versement: Mapped[MethodeVersement] = mapped_column(
        Enum(MethodeVersement, name="methode_versement"), nullable=False
    )
    # Doc §5.3ter : renseigne automatiquement a la creation si un ChequeGarantie en statut
    # confirme_par_donneur_ordre ou remis_au_partenaire existe pour la facture — facteur de
    # risque positif affiche au partenaire, jamais un ajustement automatique du calcul.
    garantie_detenue_avant_financement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    facture: Mapped["Facture"] = relationship(back_populates="avance")
    partenaire_financier: Mapped["Entreprise"] = relationship(foreign_keys=[partenaire_financier_id])
    grille_tarifaire: Mapped["GrilleTarifaire"] = relationship()
    remboursements: Mapped[list["Remboursement"]] = relationship(back_populates="avance")
