from decimal import Decimal

from app.models.enums import RoleUtilisateur, TypeEntreprise

from .factories import auth_headers, creer_entreprise, creer_facture, creer_utilisateur


def _admin(db):
    entreprise_admin = creer_entreprise(db, type=TypeEntreprise.PME, raison_sociale="InvoiceUp Plateforme")
    return creer_utilisateur(db, entreprise=entreprise_admin, role=RoleUtilisateur.ADMIN)


def test_sessions_listees_apres_login_et_revocation(client, db_session):
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)
    admin = _admin(db_session)

    login = client.post("/auth/login", json={"telephone": membre.telephone, "mot_de_passe": "MotDePasse123!"})
    assert login.status_code == 200, login.text

    r = client.get(f"/admin/utilisateurs/{membre.id}/sessions", headers=auth_headers(admin))
    assert r.status_code == 200, r.text
    sessions = r.json()
    assert len(sessions) == 1
    assert sessions[0]["revoked"] is False
    assert sessions[0]["user_agent"] is not None

    session_id = sessions[0]["id"]
    revoke = client.post(f"/admin/sessions/{session_id}/revoquer", headers=auth_headers(admin))
    assert revoke.status_code == 204, revoke.text

    r2 = client.get(f"/admin/utilisateurs/{membre.id}/sessions", headers=auth_headers(admin))
    assert r2.json()[0]["revoked"] is True


def test_revoquer_toutes_les_sessions(client, db_session):
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)
    admin = _admin(db_session)

    client.post("/auth/login", json={"telephone": membre.telephone, "mot_de_passe": "MotDePasse123!"})
    client.post("/auth/login", json={"telephone": membre.telephone, "mot_de_passe": "MotDePasse123!"})

    r = client.post(f"/admin/utilisateurs/{membre.id}/sessions/revoquer-tout", headers=auth_headers(admin))
    assert r.status_code == 204, r.text

    sessions = client.get(f"/admin/utilisateurs/{membre.id}/sessions", headers=auth_headers(admin)).json()
    assert all(s["revoked"] for s in sessions)


def test_journal_audit_liste_et_filtre(client, db_session):
    admin = _admin(db_session)
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)

    r = client.get("/admin/journal-audit?entite_type=Entreprise", headers=auth_headers(admin))
    assert r.status_code == 200, r.text
    assert all(item["entite_type"] == "Entreprise" for item in r.json())


def test_transactions_supervision_reflete_les_factures(client, db_session):
    admin = _admin(db_session)
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME, raison_sociale="Fournisseur Test")
    donneur = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE, raison_sociale="Acheteur Test")
    facture = creer_facture(db_session, pme=pme, donneur_ordre=donneur, montant=Decimal("250000"))

    r = client.get("/admin/transactions", headers=auth_headers(admin))
    assert r.status_code == 200, r.text
    refs = {item["facture_id"] for item in r.json()}
    assert str(facture.id) in refs
    ligne = next(item for item in r.json() if item["facture_id"] == str(facture.id))
    assert ligne["fournisseur"] == "Fournisseur Test"
    assert ligne["acheteur"] == "Acheteur Test"
    assert ligne["avance_id"] is None


def test_rapport_periode_structure(client, db_session):
    admin = _admin(db_session)

    r = client.get("/admin/rapports?periode=mois", headers=auth_headers(admin))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["periode"] == "mois"
    assert "montant_total_avance_verse" in body

    bad = client.get("/admin/rapports?periode=annee", headers=auth_headers(admin))
    assert bad.status_code == 422, bad.text


def test_faq_crud(client, db_session):
    admin = _admin(db_session)

    create = client.post(
        "/faq",
        json={"question": "Comment corriger un NINEA ?", "reponse": "Contactez le support.", "portee": "pme"},
        headers=auth_headers(admin),
    )
    assert create.status_code == 201, create.text
    article_id = create.json()["id"]

    bad_portee = client.post(
        "/faq",
        json={"question": "Question invalide", "reponse": "...", "portee": "inconnue"},
        headers=auth_headers(admin),
    )
    assert bad_portee.status_code == 422, bad_portee.text

    listing = client.get("/faq", headers=auth_headers(admin))
    assert listing.status_code == 200
    assert any(a["id"] == article_id for a in listing.json())

    update = client.put(f"/faq/{article_id}", json={"publie": False}, headers=auth_headers(admin))
    assert update.status_code == 200, update.text
    assert update.json()["publie"] is False

    delete = client.delete(f"/faq/{article_id}", headers=auth_headers(admin))
    assert delete.status_code == 204, delete.text
