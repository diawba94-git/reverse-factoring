from decimal import Decimal

from app.models.enums import RoleUtilisateur, TypeEntreprise, TypeLimite
from app.models.limite_credit import LimiteCredit

from .factories import auth_headers, creer_entreprise, creer_facture, creer_grille_active, creer_utilisateur


def _admin(db):
    entreprise_admin = creer_entreprise(db, type=TypeEntreprise.PME, raison_sociale="InvoiceUp Plateforme")
    return creer_utilisateur(db, entreprise=entreprise_admin, role=RoleUtilisateur.ADMIN)


def _setup_avance_en_attente(db, montant=Decimal("10000000"), duree_jours=60):
    pme = creer_entreprise(db, type=TypeEntreprise.PME)
    donneur = creer_entreprise(db, type=TypeEntreprise.GRANDE_ENTREPRISE)
    partenaire = creer_entreprise(db, type=TypeEntreprise.PARTENAIRE_FINANCIER)
    agent = creer_utilisateur(db, entreprise=partenaire, role=RoleUtilisateur.AGENT_FINANCIER)
    membre = creer_utilisateur(db, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)
    creer_grille_active(db)
    from app.models.enums import StatutFacture

    facture = creer_facture(db, pme=pme, donneur_ordre=donneur, montant=montant, duree_jours=duree_jours, statut=StatutFacture.VALIDEE)
    db.commit()
    return pme, donneur, partenaire, agent, membre, facture


def test_enveloppe_insuffisante_bloque_approbation(client, db_session):
    admin = _admin(db_session)
    pme, donneur, partenaire, agent, membre, facture = _setup_avance_en_attente(db_session, montant=Decimal("100000000"))

    client.put(
        f"/enveloppes/{partenaire.id}",
        json={"montant_total_alloue": "1000000"},
        headers=auth_headers(admin),
    )

    demande = client.post(
        "/avances",
        json={"facture_id": str(facture.id), "partenaire_financier_id": str(partenaire.id), "methode_versement": "wave"},
        headers=auth_headers(membre),
    )
    assert demande.status_code == 201, demande.text
    avance_id = demande.json()["id"]

    approbation = client.post(f"/avances/{avance_id}/approuver", headers=auth_headers(agent))
    assert approbation.status_code == 422, approbation.text
    assert "Enveloppe insuffisante" in approbation.text


def test_limite_credit_acheteur_bloque_approbation(client, db_session):
    pme, donneur, partenaire, agent, membre, facture = _setup_avance_en_attente(db_session, montant=Decimal("10000000"))

    db_session.add(
        LimiteCredit(
            partenaire_financier_id=partenaire.id,
            entreprise_cible_id=donneur.id,
            type_limite=TypeLimite.ACHETEUR,
            montant_plafond=Decimal("1000000"),
            montant_utilise=Decimal("0"),
        )
    )
    db_session.commit()

    demande = client.post(
        "/avances",
        json={"facture_id": str(facture.id), "partenaire_financier_id": str(partenaire.id), "methode_versement": "wave"},
        headers=auth_headers(membre),
    )
    avance_id = demande.json()["id"]

    approbation = client.post(f"/avances/{avance_id}/approuver", headers=auth_headers(agent))
    assert approbation.status_code == 422, approbation.text
    assert "Limite de crédit" in approbation.text


def test_approbation_incremente_la_limite_utilisee(client, db_session):
    pme, donneur, partenaire, agent, membre, facture = _setup_avance_en_attente(db_session, montant=Decimal("1000000"))

    limite = LimiteCredit(
        partenaire_financier_id=partenaire.id,
        entreprise_cible_id=donneur.id,
        type_limite=TypeLimite.ACHETEUR,
        montant_plafond=Decimal("50000000"),
        montant_utilise=Decimal("0"),
    )
    db_session.add(limite)
    db_session.commit()

    demande = client.post(
        "/avances",
        json={"facture_id": str(facture.id), "partenaire_financier_id": str(partenaire.id), "methode_versement": "wave"},
        headers=auth_headers(membre),
    )
    avance_id = demande.json()["id"]
    montant_avance_initial = Decimal(demande.json()["montant_avance_initial"])

    approbation = client.post(f"/avances/{avance_id}/approuver", headers=auth_headers(agent))
    assert approbation.status_code == 200, approbation.text

    db_session.refresh(limite)
    assert limite.montant_utilise == montant_avance_initial


def test_dossier_decision_contient_les_verifications(client, db_session):
    pme, donneur, partenaire, agent, membre, facture = _setup_avance_en_attente(db_session)

    demande = client.post(
        "/avances",
        json={"facture_id": str(facture.id), "partenaire_financier_id": str(partenaire.id), "methode_versement": "wave"},
        headers=auth_headers(membre),
    )
    avance_id = demande.json()["id"]

    dossier = client.get(f"/avances/{avance_id}/dossier-decision", headers=auth_headers(agent))
    assert dossier.status_code == 200, dossier.text
    corps = dossier.json()
    assert corps["pme_raison_sociale"] == pme.raison_sociale
    assert corps["donneur_ordre_raison_sociale"] == donneur.raison_sociale
    # La relation n'est auto-creee que par le vrai flux de creation de facture
    # (POST /factures/native) ; ce test insere la facture directement via la factory.
    assert corps["relation_statut"] is None
    assert corps["cheque"] is None
    assert corps["historique_cycles_rembourses"] == 0


def test_agent_financier_ne_voit_pas_le_dossier_dune_autre_avance(client, db_session):
    pme, donneur, partenaire, agent, membre, facture = _setup_avance_en_attente(db_session)
    autre_partenaire = creer_entreprise(db_session, type=TypeEntreprise.PARTENAIRE_FINANCIER)
    autre_agent = creer_utilisateur(db_session, entreprise=autre_partenaire, role=RoleUtilisateur.AGENT_FINANCIER)

    demande = client.post(
        "/avances",
        json={"facture_id": str(facture.id), "partenaire_financier_id": str(partenaire.id), "methode_versement": "wave"},
        headers=auth_headers(membre),
    )
    avance_id = demande.json()["id"]

    r = client.get(f"/avances/{avance_id}/dossier-decision", headers=auth_headers(autre_agent))
    assert r.status_code == 403
