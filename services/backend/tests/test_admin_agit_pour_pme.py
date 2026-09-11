from datetime import date, timedelta

from app.models.enums import RoleUtilisateur, TypeEntreprise

from .factories import auth_headers, creer_entreprise, creer_utilisateur


def _admin(db):
    entreprise_admin = creer_entreprise(db, type=TypeEntreprise.PME, raison_sociale="InvoiceUp Plateforme")
    return creer_utilisateur(db, entreprise=entreprise_admin, role=RoleUtilisateur.ADMIN)


def _payload_native(donneur_id, pme_id=None):
    emission = date.today()
    payload = {
        "donneur_ordre_id": str(donneur_id),
        "date_emission": emission.isoformat(),
        "date_echeance": (emission + timedelta(days=45)).isoformat(),
        "taux_tva": "0.18",
        "lignes": [{"designation": "Article", "quantite": "1", "prix_unitaire": "1000.00"}],
    }
    if pme_id is not None:
        payload["pme_id"] = str(pme_id)
    return payload


def test_admin_doit_fournir_pme_id_sinon_422(client, db_session):
    admin = _admin(db_session)
    donneur = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE)

    r = client.post("/factures/native", json=_payload_native(donneur.id), headers=auth_headers(admin))
    assert r.status_code == 422, r.text
    assert "pme_id" in r.json()["detail"]


def test_admin_peut_creer_facture_native_pour_une_pme_choisie(client, db_session):
    admin = _admin(db_session)
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME, raison_sociale="PME Choisie")
    donneur = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE)

    r = client.post(
        "/factures/native", json=_payload_native(donneur.id, pme_id=pme.id), headers=auth_headers(admin)
    )
    assert r.status_code == 201, r.text
    assert r.json()["pme_id"] == str(pme.id)

    listing = client.get(f"/factures?pme_id={pme.id}", headers=auth_headers(admin))
    assert listing.status_code == 200, listing.text
    assert len(listing.json()) == 1
    assert listing.json()[0]["pme_id"] == str(pme.id)


def test_membre_pme_ne_peut_pas_usurper_un_autre_pme_id(client, db_session):
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME, raison_sociale="Ma PME")
    autre_pme = creer_entreprise(db_session, type=TypeEntreprise.PME, raison_sociale="Autre PME")
    donneur = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE)
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)

    r = client.post(
        "/factures/native", json=_payload_native(donneur.id, pme_id=autre_pme.id), headers=auth_headers(membre)
    )
    assert r.status_code == 201, r.text
    # pme_id fourni par un membre_pme est ignore : la facture appartient a SA propre entreprise
    assert r.json()["pme_id"] == str(pme.id)
    assert r.json()["pme_id"] != str(autre_pme.id)


def test_membre_pme_peut_lister_ses_propres_collegues(client, db_session):
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    autre_pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)
    collegue = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)
    creer_utilisateur(db_session, entreprise=autre_pme, role=RoleUtilisateur.MEMBRE_PME)

    r = client.get("/utilisateurs", headers=auth_headers(membre))
    assert r.status_code == 200, r.text
    ids = {u["id"] for u in r.json()}
    assert str(membre.id) in ids
    assert str(collegue.id) in ids
    assert len(r.json()) == 2  # jamais les utilisateurs de l'autre PME


def test_membre_pme_ne_peut_pas_forcer_entreprise_id_dans_le_filtre(client, db_session):
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    autre_pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)
    creer_utilisateur(db_session, entreprise=autre_pme, role=RoleUtilisateur.MEMBRE_PME)

    r = client.get(f"/utilisateurs?entreprise_id={autre_pme.id}", headers=auth_headers(membre))
    assert r.status_code == 200, r.text
    for u in r.json():
        assert u["entreprise_id"] == str(pme.id)
