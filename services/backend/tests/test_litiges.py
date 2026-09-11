from decimal import Decimal

from app.models.enums import RoleUtilisateur, StatutFacture, TypeEntreprise

from .factories import auth_headers, creer_entreprise, creer_facture, creer_utilisateur


def _admin(db):
    entreprise_admin = creer_entreprise(db, type=TypeEntreprise.PME, raison_sociale="InvoiceUp Plateforme")
    return creer_utilisateur(db, entreprise=entreprise_admin, role=RoleUtilisateur.ADMIN)


def _facture_soldee(db):
    pme = creer_entreprise(db, type=TypeEntreprise.PME, raison_sociale="AgroFarma")
    donneur_ordre = creer_entreprise(db, type=TypeEntreprise.GRANDE_ENTREPRISE, raison_sociale="CSE")
    return creer_facture(db, pme=pme, donneur_ordre=donneur_ordre, statut=StatutFacture.AVANCE_VERSEE)


def test_ouverture_litige_bascule_la_facture_en_litige(client, db_session):
    admin = _admin(db_session)
    facture = _facture_soldee(db_session)
    db_session.commit()

    r = client.post(
        "/litiges",
        json={
            "facture_id": str(facture.id),
            "cause": "cheque_sans_provision",
            "montant_en_jeu": "12300000",
            "description": "Cheque rejete pour absence de provision.",
        },
        headers=auth_headers(admin),
    )
    assert r.status_code == 201, r.text
    dossier = r.json()
    assert dossier["statut"] == "ouvert"
    assert dossier["fournisseur"] == "AgroFarma"
    assert dossier["acheteur"] == "CSE"

    facture_apres = client.get(f"/factures/{facture.id}", headers=auth_headers(admin)).json()
    assert facture_apres["statut"] == "litige"


def test_ouverture_refusee_si_deja_en_litige(client, db_session):
    admin = _admin(db_session)
    facture = _facture_soldee(db_session)
    facture.statut = StatutFacture.LITIGE
    db_session.commit()

    r = client.post(
        "/litiges",
        json={
            "facture_id": str(facture.id),
            "cause": "autre",
            "montant_en_jeu": "1000",
            "description": "x",
        },
        headers=auth_headers(admin),
    )
    assert r.status_code == 409, r.text


def test_marquer_resolu_restaure_le_statut_facture_precedent(client, db_session):
    admin = _admin(db_session)
    facture = _facture_soldee(db_session)
    db_session.commit()

    ouverture = client.post(
        "/litiges",
        json={
            "facture_id": str(facture.id),
            "cause": "ecart_remboursement",
            "montant_en_jeu": "840000",
            "description": "Ecart detecte au rapprochement.",
        },
        headers=auth_headers(admin),
    )
    litige_id = ouverture.json()["id"]

    resolution = client.patch(
        f"/litiges/{litige_id}",
        json={"action": "marquer_resolu", "resolution_note": "Ecart justifie et regularise."},
        headers=auth_headers(admin),
    )
    assert resolution.status_code == 200, resolution.text
    assert resolution.json()["statut"] == "resolu"

    facture_apres = client.get(f"/factures/{facture.id}", headers=auth_headers(admin)).json()
    assert facture_apres["statut"] == "avance_versee"


def test_action_intermediaire_passe_le_dossier_en_cours(client, db_session):
    admin = _admin(db_session)
    facture = _facture_soldee(db_session)
    db_session.commit()

    litige_id = client.post(
        "/litiges",
        json={
            "facture_id": str(facture.id),
            "cause": "contestation_acheteur",
            "montant_en_jeu": "30000000",
            "description": "Contestation partielle de la livraison.",
        },
        headers=auth_headers(admin),
    ).json()["id"]

    r = client.patch(
        f"/litiges/{litige_id}",
        json={"action": "contacter_parties"},
        headers=auth_headers(admin),
    )
    assert r.status_code == 200, r.text
    assert r.json()["statut"] == "en_cours"
    assert r.json()["derniere_action"] == "contacter_parties"


def test_non_admin_ne_peut_pas_ouvrir_de_litige(client, db_session):
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)
    facture = _facture_soldee(db_session)
    db_session.commit()

    r = client.post(
        "/litiges",
        json={
            "facture_id": str(facture.id),
            "cause": "autre",
            "montant_en_jeu": "1000",
            "description": "x",
        },
        headers=auth_headers(membre),
    )
    assert r.status_code == 403
