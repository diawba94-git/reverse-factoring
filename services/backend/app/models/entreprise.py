import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import FormeJuridique, StatutFiche, StatutKyc, TypeEntreprise


class Entreprise(Base):
    __tablename__ = "entreprises"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type: Mapped[TypeEntreprise] = mapped_column(Enum(TypeEntreprise, name="type_entreprise"), nullable=False)
    raison_sociale: Mapped[str] = mapped_column(String(255), nullable=False)
    # Nullable : une fiche acheteur "minimale" (statut_fiche=pre_inscrite, creee par une PME
    # qui lui adresse une premiere facture, voir doc §3.0quater) n'a encore ni NINEA, ni
    # secteur, ni coordonnees propres — l'acheteur les renseigne lui-meme a l'onboarding.
    ninea: Mapped[str | None] = mapped_column(String(50), nullable=True)
    forme_juridique: Mapped[FormeJuridique | None] = mapped_column(
        Enum(FormeJuridique, name="forme_juridique", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=True,
    )
    # Nullable en base pour ne pas invalider les entreprises existantes creees avant
    # l'introduction de forme_juridique : le NINEA reste le seul identifiant legal
    # obligatoire, le RCCM n'est requis (en validation applicative) que pour certaines
    # formes juridiques (voir app.services.kyc.rccm_est_obligatoire).
    rccm: Mapped[str | None] = mapped_column(String(50), nullable=True)
    statut_kyc: Mapped[StatutKyc] = mapped_column(
        Enum(StatutKyc, name="statut_kyc"), nullable=False, default=StatutKyc.EN_ATTENTE
    )
    secteur_activite: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chiffre_affaires: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    date_creation: Mapped[date | None] = mapped_column(Date, nullable=True)
    contact_telephone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # contact_telephone/contact_email jouent deja le role de "telephone"/"email" demandes
    # pour l'en-tete des factures generees ; seule l'adresse postale manquait reellement.
    adresse: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Fiche acheteur minimale (voir statut_fiche) : contact designe par la PME pour
    # l'invitation, avant que l'acheteur n'ait lui-meme cree son compte.
    contact_invitation_nom: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_invitation_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_invitation_envoyee: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Jeton a usage unique permettant au contact invite de rejoindre cette fiche minimale
    # comme premier validateur (voir POST /auth/rejoindre-entreprise/{token}) ; efface une
    # fois utilise.
    token_invitation_initiale: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)

    kyc_document_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    motif_rejet_kyc: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # Statut de fiche : distinct du KYC. Une PME/un partenaire s'inscrit toujours en ACTIVE ;
    # seul un acheteur cree ad-hoc par une PME (fiche minimale, avant que l'acheteur n'ait
    # lui-meme rejoint la plateforme) transite par PRE_INSCRITE (voir doc §3.0quater).
    statut_fiche: Mapped[StatutFiche] = mapped_column(
        Enum(StatutFiche, name="statut_fiche"), nullable=False, default=StatutFiche.ACTIVE
    )
    cree_par_entreprise_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entreprises.id", ondelete="SET NULL"), nullable=True
    )
    # Desactivee (jamais supprimee, pour la tracabilite) lors d'une fusion de doublons
    # admin : voir POST /admin/doublons/fusionner.
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    utilisateurs: Mapped[list["Utilisateur"]] = relationship(
        back_populates="entreprise", foreign_keys="Utilisateur.entreprise_id"
    )
