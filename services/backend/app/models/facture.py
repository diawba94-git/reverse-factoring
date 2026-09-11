import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import SourceCreationFacture, StatutFacture


class Facture(Base):
    __tablename__ = "factures"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero_facture: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Attribue par l'outil (jamais saisi) au moment de la transmission au donneur d'ordre ; "
        "absent tant que la facture est au statut brouillon.",
    )
    pme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entreprises.id", ondelete="RESTRICT"), nullable=False
    )
    donneur_ordre_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entreprises.id", ondelete="RESTRICT"), nullable=False
    )
    montant_ht: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    taux_tva: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0.18"))
    montant_tva: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    montant_ttc: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    devise: Mapped[str] = mapped_column(String(10), nullable=False, default="FCFA")
    date_emission: Mapped[date] = mapped_column(Date, nullable=False)
    date_echeance: Mapped[date] = mapped_column(Date, nullable=False)
    duree_jours: Mapped[int] = mapped_column(Integer, nullable=False)
    statut: Mapped[StatutFacture] = mapped_column(
        Enum(StatutFacture, name="statut_facture"), nullable=False, default=StatutFacture.EMISE
    )
    piece_justificative_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    source_creation: Mapped[SourceCreationFacture] = mapped_column(
        Enum(SourceCreationFacture, name="source_creation_facture"), nullable=False
    )

    # Controle de conformite automatique (voir app.services.conformite_facture) : champs
    # extraits du PDF televerse et compares aux donnees declarees (NINEA de l'entreprise,
    # coherence HT/TVA/TTC) avant qu'une facture ne puisse atteindre le statut `emise`.
    ninea_emetteur_extrait: Mapped[str | None] = mapped_column(String(20), nullable=True)
    code_validation_dgid: Mapped[str | None] = mapped_column(String(255), nullable=True)
    conformite_verifiee: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    motifs_rejet_conformite: Mapped[list | None] = mapped_column(JSON, nullable=True)

    date_derniere_maj: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pme: Mapped["Entreprise"] = relationship(foreign_keys=[pme_id])
    donneur_ordre: Mapped["Entreprise"] = relationship(foreign_keys=[donneur_ordre_id])
    validations: Mapped[list["ValidationFacture"]] = relationship(back_populates="facture")
    avance: Mapped["Avance"] = relationship(back_populates="facture", uselist=False)
    messages: Mapped[list["MessageFacture"]] = relationship(back_populates="facture")
    lignes: Mapped[list["LigneFacture"]] = relationship(
        back_populates="facture", order_by="LigneFacture.ordre", cascade="all, delete-orphan"
    )
    cheque_garantie: Mapped["ChequeGarantie | None"] = relationship(back_populates="facture", uselist=False)
    avoirs: Mapped[list["AvoirFacture"]] = relationship(back_populates="facture")
