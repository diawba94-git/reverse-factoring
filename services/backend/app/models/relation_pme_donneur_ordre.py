import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import StatutRelation


class RelationPmeDonneurOrdre(Base):
    """Relation commerciale PME<->donneur d'ordre, portee par relation et non par facture
    (doc §5.4) : onboarding progressif pilote (quota de factures sans engagement structurel)
    puis convention_signee (domiciliation complete). Sert aussi a afficher le statut
    Pilote/Signee dans les dashboards admin et partenaire.

    Simplification assumee pour ce MVP : la double validation des factures reste scopee a
    l'entreprise donneur d'ordre entiere (voir POST /factures/{id}/valider), pas encore
    restreinte aux seuls validateurs affectes a la relation concernee — ValidateurRelation
    trace neanmoins ces affectations pour une evolution future sans nouvelle migration.
    """

    __tablename__ = "relations_pme_donneur_ordre"
    __table_args__ = (UniqueConstraint("pme_id", "donneur_ordre_id", name="uq_relation_pme_donneur_ordre"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entreprises.id", ondelete="CASCADE"), nullable=False
    )
    donneur_ordre_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entreprises.id", ondelete="CASCADE"), nullable=False
    )
    statut: Mapped[StatutRelation] = mapped_column(
        Enum(StatutRelation, name="statut_relation"), nullable=False, default=StatutRelation.PILOTE
    )
    factures_pilote_max: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    factures_pilote_utilisees: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    date_debut_relation: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pme: Mapped["Entreprise"] = relationship(foreign_keys=[pme_id])
    donneur_ordre: Mapped["Entreprise"] = relationship(foreign_keys=[donneur_ordre_id])
    validateurs: Mapped[list["ValidateurRelation"]] = relationship(back_populates="relation")


class ValidateurRelation(Base):
    """Affecte un validateur_1/validateur_2 a une RelationPmeDonneurOrdre precise (doc §5.4) :
    trace la portee, meme si l'autorisation de validation elle-meme reste au niveau de
    l'entreprise entiere pour ce MVP (voir docstring de RelationPmeDonneurOrdre)."""

    __tablename__ = "validateurs_relation"
    __table_args__ = (UniqueConstraint("relation_id", "utilisateur_id", name="uq_validateur_relation"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    relation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("relations_pme_donneur_ordre.id", ondelete="CASCADE"), nullable=False
    )
    utilisateur_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("utilisateurs.id", ondelete="CASCADE"), nullable=False
    )
    date_affectation: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    relation: Mapped["RelationPmeDonneurOrdre"] = relationship(back_populates="validateurs")
    utilisateur: Mapped["Utilisateur"] = relationship()
