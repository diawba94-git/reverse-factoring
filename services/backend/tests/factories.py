"""Test-only helpers for building fixtures directly via the ORM (faster and more direct
than going through the HTTP API for setup), plus a shortcut to mint a valid access token
without exercising the full login/MFA flow."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.entreprise import Entreprise
from app.models.enums import FormeJuridique, RoleUtilisateur, StatutFacture, StatutFiche, StatutKyc, TypeEntreprise
from app.models.facture import Facture
from app.models.grille_tarifaire import GrilleTarifaire
from app.models.utilisateur import Utilisateur
from app.security import create_access_token, hash_password


def creer_entreprise(
    db: Session,
    *,
    type: TypeEntreprise,
    raison_sociale: str = "Test SARL",
    statut_kyc: StatutKyc = StatutKyc.VALIDE,
    forme_juridique: FormeJuridique | None = None,
    rccm: str | None = None,
    kyc_document_url: str | None = None,
    ninea: str | None = None,
    adresse: str = "123 Rue Test, Dakar, Senegal",
    contact_telephone: str | None = None,
    statut_fiche: StatutFiche = StatutFiche.ACTIVE,
    cree_par_entreprise_id=None,
    actif: bool = True,
) -> Entreprise:
    entreprise = Entreprise(
        type=type,
        raison_sociale=raison_sociale,
        ninea=ninea or str(uuid.uuid4().int)[:9],
        forme_juridique=forme_juridique,
        rccm=rccm,
        statut_kyc=statut_kyc,
        secteur_activite="Test",
        date_creation=date.today(),
        contact_telephone=contact_telephone or f"+2217{uuid.uuid4().int % 10**8:08d}",
        contact_email="test@example.sn",
        kyc_document_url=kyc_document_url,
        adresse=adresse,
        statut_fiche=statut_fiche,
        cree_par_entreprise_id=cree_par_entreprise_id,
        actif=actif,
    )
    db.add(entreprise)
    db.flush()
    return entreprise


def creer_utilisateur(
    db: Session,
    *,
    entreprise: Entreprise,
    role: RoleUtilisateur,
    telephone: str | None = None,
    compte_actif: bool = True,
) -> Utilisateur:
    utilisateur = Utilisateur(
        entreprise_id=entreprise.id,
        role=role,
        nom="Utilisateur Test",
        telephone=telephone or f"+2217{uuid.uuid4().int % 10**8:08d}",
        email="user@example.sn",
        mot_de_passe_hash=hash_password("MotDePasse123!"),
        compte_actif=compte_actif,
    )
    db.add(utilisateur)
    db.flush()
    return utilisateur


def token_pour(utilisateur: Utilisateur) -> str:
    return create_access_token(str(utilisateur.id), utilisateur.role.value)


def auth_headers(utilisateur: Utilisateur) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_pour(utilisateur)}"}


def creer_grille_active(db: Session) -> GrilleTarifaire:
    grille = GrilleTarifaire(
        nom="Grille test",
        taux_total_minimum=Decimal("0.023"),
        taux_total_maximum=Decimal("0.03"),
        proportion_cedra=Decimal("0.3333"),
        proportion_partenaire=Decimal("0.6667"),
        plafond_montant=None,
        duree_minimum_jours=60,
        duree_maximum_jours=90,
        taux_avance=Decimal("0.80"),
        active=True,
        date_debut_validite=date.today(),
    )
    db.add(grille)
    db.flush()
    return grille


def creer_facture(
    db: Session,
    *,
    pme: Entreprise,
    donneur_ordre: Entreprise,
    montant: Decimal = Decimal("100000"),
    duree_jours: int = 60,
    statut: StatutFacture = StatutFacture.EMISE,
) -> Facture:
    from datetime import timedelta

    from app.models.enums import SourceCreationFacture

    emission = date.today()
    montant_ht = (montant / Decimal("1.18")).quantize(Decimal("0.01"))
    montant_tva = montant - montant_ht
    facture = Facture(
        pme_id=pme.id,
        numero_facture=f"FAC-TEST-{uuid.uuid4().hex[:8]}",
        donneur_ordre_id=donneur_ordre.id,
        montant_ht=montant_ht,
        taux_tva=Decimal("0.18"),
        montant_tva=montant_tva,
        montant_ttc=montant,
        devise="FCFA",
        date_emission=emission,
        date_echeance=emission + timedelta(days=duree_jours),
        duree_jours=duree_jours,
        piece_justificative_url="https://example.com/facture.pdf",
        source_creation=SourceCreationFacture.SAISIE_MANUELLE,
        conformite_verifiee=True,
        statut=statut,
    )
    db.add(facture)
    db.flush()
    return facture
