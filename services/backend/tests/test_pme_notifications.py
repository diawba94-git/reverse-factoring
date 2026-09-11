from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.avance import Avance
from app.models.enums import (
    MethodeVersement,
    RoleUtilisateur,
    RoleValidateur,
    StatutAvance,
    StatutFacture,
    TypeEntreprise,
)
from app.models.validation_facture import ValidationFacture

from .factories import auth_headers, creer_entreprise, creer_facture, creer_grille_active, creer_utilisateur


def test_notification_validation_en_cours_pour_facture_partiellement_validee(db_session, client):
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    donneur = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE, raison_sociale="Sonatel")
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)
    validateur = creer_utilisateur(db_session, entreprise=donneur, role=RoleUtilisateur.VALIDATEUR_1)
    facture = creer_facture(db_session, pme=pme, donneur_ordre=donneur, statut=StatutFacture.EMISE)
    facture.numero_facture = "FAC-2608-041"
    db_session.add(
        ValidationFacture(facture_id=facture.id, utilisateur_id=validateur.id, role_validateur=RoleValidateur.VALIDATEUR_1)
    )
    db_session.commit()

    r = client.get("/pme/notifications", headers=auth_headers(membre))
    assert r.status_code == 200, r.text
    corps = r.json()
    validations = [n for n in corps if n["type"] == "validation"]
    assert len(validations) == 1
    assert "FAC-2608-041" in validations[0]["titre"]
    assert "Sonatel" in validations[0]["description"]


def test_notification_financement_pour_avance_versee(db_session, client):
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    donneur = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE)
    partenaire = creer_entreprise(db_session, type=TypeEntreprise.PARTENAIRE_FINANCIER)
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)
    grille = creer_grille_active(db_session)
    facture = creer_facture(db_session, pme=pme, donneur_ordre=donneur, montant=Decimal("15500000"), statut=StatutFacture.VALIDEE)

    avance = Avance(
        facture_id=facture.id,
        partenaire_financier_id=partenaire.id,
        grille_tarifaire_id=grille.id,
        montant_avance_initial=Decimal("12400000"),
        frais_total=Decimal("230000"),
        montant_solde_du=Decimal("2870000"),
        part_partenaire=Decimal("153300"),
        part_plateforme=Decimal("76700"),
        taeg_annualise=Decimal("0.1399"),
        statut=StatutAvance.AVANCE_VERSEE,
        methode_versement=MethodeVersement.WAVE,
        garantie_detenue_avant_financement=False,
        date_versement_initial=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db_session.add(avance)
    db_session.commit()

    r = client.get("/pme/notifications", headers=auth_headers(membre))
    assert r.status_code == 200, r.text
    corps = r.json()
    financements = [n for n in corps if n["type"] == "financement"]
    assert len(financements) == 1
    assert "avancée" in financements[0]["titre"]
    assert financements[0]["lu"] is False


def test_notifications_pme_refusees_pour_role_non_membre_pme(db_session, client):
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    admin = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.ADMIN)
    db_session.commit()

    r = client.get("/pme/notifications", headers=auth_headers(admin))
    assert r.status_code == 403
