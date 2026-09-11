from app.models.enums import RoleUtilisateur, TypeEntreprise

from .factories import auth_headers, creer_entreprise, creer_utilisateur


def _admin(db):
    entreprise_admin = creer_entreprise(db, type=TypeEntreprise.PME, raison_sociale="InvoiceUp Plateforme")
    return creer_utilisateur(db, entreprise=entreprise_admin, role=RoleUtilisateur.ADMIN)


def test_admin_cree_un_utilisateur_avec_role_coherent_et_compte_actif(client, db_session):
    admin = _admin(db_session)
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)

    r = client.post(
        f"/admin/entreprises/{pme.id}/utilisateurs",
        json={"nom": "Nouveau Membre", "telephone": "+221701234567", "email": "n@example.sn", "role": "membre_pme"},
        headers=auth_headers(admin),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["compte_actif"] is True
    assert body["role"] == "membre_pme"
    assert len(body["mot_de_passe_temporaire"]) > 0


def test_admin_rejette_role_incoherent_avec_le_type_entreprise(client, db_session):
    admin = _admin(db_session)
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)

    r = client.post(
        f"/admin/entreprises/{pme.id}/utilisateurs",
        json={"nom": "Intrus", "telephone": "+221701234568", "email": "i@example.sn", "role": "validateur_1"},
        headers=auth_headers(admin),
    )
    assert r.status_code == 422, r.text
    assert "validateur_1" in r.json()["detail"]


def test_admin_ne_peut_jamais_attribuer_le_role_admin(client, db_session):
    admin = _admin(db_session)
    partenaire = creer_entreprise(db_session, type=TypeEntreprise.PARTENAIRE_FINANCIER)

    r = client.post(
        f"/admin/entreprises/{partenaire.id}/utilisateurs",
        json={"nom": "Faux Admin", "telephone": "+221701234569", "email": "f@example.sn", "role": "admin"},
        headers=auth_headers(admin),
    )
    assert r.status_code == 422, r.text


def test_non_admin_ne_peut_pas_utiliser_cet_endpoint(client, db_session):
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)

    r = client.post(
        f"/admin/entreprises/{pme.id}/utilisateurs",
        json={"nom": "X", "telephone": "+221701234570", "email": "x@example.sn", "role": "membre_pme"},
        headers=auth_headers(membre),
    )
    assert r.status_code == 403, r.text


def test_admin_modifie_role_avec_controle_de_coherence(client, db_session):
    admin = _admin(db_session)
    donneur = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE)
    v1 = creer_utilisateur(db_session, entreprise=donneur, role=RoleUtilisateur.VALIDATEUR_1)

    ok = client.patch(f"/admin/utilisateurs/{v1.id}", json={"role": "validateur_2"}, headers=auth_headers(admin))
    assert ok.status_code == 200, ok.text
    assert ok.json()["role"] == "validateur_2"

    bad = client.patch(f"/admin/utilisateurs/{v1.id}", json={"role": "membre_pme"}, headers=auth_headers(admin))
    assert bad.status_code == 422, bad.text


def test_admin_desactive_et_reactive_un_compte(client, db_session):
    admin = _admin(db_session)
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)

    off = client.patch(f"/admin/utilisateurs/{membre.id}", json={"compte_actif": False}, headers=auth_headers(admin))
    assert off.status_code == 200, off.text
    assert off.json()["compte_actif"] is False

    on = client.patch(f"/admin/utilisateurs/{membre.id}", json={"compte_actif": True}, headers=auth_headers(admin))
    assert on.status_code == 200, on.text
    assert on.json()["compte_actif"] is True


def test_suppression_physique_bloquee_si_utilisateur_a_des_actions_auditees(client, db_session):
    admin = _admin(db_session)
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)

    # Genere une entree JournalAudit pour cet utilisateur via une action admin.
    client.patch(f"/admin/utilisateurs/{membre.id}", json={"compte_actif": False}, headers=auth_headers(admin))

    r = client.delete(f"/utilisateurs/{membre.id}", headers=auth_headers(admin))
    assert r.status_code == 409, r.text
