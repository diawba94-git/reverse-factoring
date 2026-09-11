from app.models.enums import FormeJuridique, RoleUtilisateur, TypeEntreprise

from .factories import auth_headers, creer_entreprise, creer_utilisateur


def _payload_entreprise(**overrides):
    payload = {
        "type": "PME",
        "raison_sociale": "Ma Boite",
        "ninea": "005912345",
        "forme_juridique": "sarl",
        "secteur_activite": "Commerce",
        "date_creation": "2020-01-01",
        "contact_telephone": "+221701112233",
        "contact_email": "contact@example.sn",
        "adresse": "123 Rue Test, Dakar, Senegal",
    }
    payload.update(overrides)
    return payload


def test_creation_entreprise_sans_ninea_est_rejetee(client, db_session):
    payload = _payload_entreprise(rccm="SN-DKR-2020-B-1234")
    del payload["ninea"]

    r = client.post("/entreprises", json=payload)
    assert r.status_code == 422, r.text


def test_creation_entreprise_sarl_sans_rccm_est_rejetee(client, db_session):
    payload = _payload_entreprise(forme_juridique="sarl")
    payload.pop("rccm", None)

    r = client.post("/entreprises", json=payload)
    assert r.status_code == 422, r.text


def test_creation_entreprise_personne_physique_sans_rccm_est_acceptee(client, db_session):
    payload = _payload_entreprise(forme_juridique="personne_physique_entreprise_individuelle")
    payload.pop("rccm", None)

    r = client.post("/entreprises", json=payload)
    assert r.status_code == 201, r.text
    assert r.json()["rccm"] is None


def test_kyc_valide_personne_physique_sans_rccm(client, db_session):
    entreprise = creer_entreprise(
        db_session,
        type=TypeEntreprise.PME,
        forme_juridique=FormeJuridique.PERSONNE_PHYSIQUE_ENTREPRISE_INDIVIDUELLE,
        rccm=None,
        kyc_document_url="/uploads/kyc/piece.pdf",
    )
    admin = creer_utilisateur(db_session, entreprise=entreprise, role=RoleUtilisateur.ADMIN)

    r = client.patch(f"/entreprises/{entreprise.id}/kyc", json={"statut_kyc": "valide"}, headers=auth_headers(admin))
    assert r.status_code == 200, r.text
    assert r.json()["statut_kyc"] == "valide"


def test_kyc_rejete_sarl_sans_rccm(client, db_session):
    entreprise = creer_entreprise(
        db_session,
        type=TypeEntreprise.PME,
        forme_juridique=FormeJuridique.SARL,
        rccm=None,
        kyc_document_url="/uploads/kyc/piece.pdf",
    )
    admin = creer_utilisateur(db_session, entreprise=entreprise, role=RoleUtilisateur.ADMIN)

    r = client.patch(f"/entreprises/{entreprise.id}/kyc", json={"statut_kyc": "valide"}, headers=auth_headers(admin))
    assert r.status_code == 422, r.text
    assert "RCCM" in r.json()["detail"]


def test_kyc_valide_sarl_avec_rccm(client, db_session):
    entreprise = creer_entreprise(
        db_session,
        type=TypeEntreprise.PME,
        forme_juridique=FormeJuridique.SARL,
        rccm="SN-DKR-2020-B-1234",
        kyc_document_url="/uploads/kyc/piece.pdf",
    )
    admin = creer_utilisateur(db_session, entreprise=entreprise, role=RoleUtilisateur.ADMIN)

    r = client.patch(f"/entreprises/{entreprise.id}/kyc", json={"statut_kyc": "valide"}, headers=auth_headers(admin))
    assert r.status_code == 200, r.text
    assert r.json()["statut_kyc"] == "valide"


def test_kyc_valide_rejete_si_forme_juridique_non_renseignee(client, db_session):
    entreprise = creer_entreprise(
        db_session,
        type=TypeEntreprise.PME,
        forme_juridique=None,
        kyc_document_url="/uploads/kyc/piece.pdf",
    )
    admin = creer_utilisateur(db_session, entreprise=entreprise, role=RoleUtilisateur.ADMIN)

    r = client.patch(f"/entreprises/{entreprise.id}/kyc", json={"statut_kyc": "valide"}, headers=auth_headers(admin))
    assert r.status_code == 422, r.text


def test_upload_kyc_rejete_si_forme_juridique_non_renseignee(client, db_session):
    entreprise = creer_entreprise(db_session, type=TypeEntreprise.PME, forme_juridique=None)
    membre = creer_utilisateur(db_session, entreprise=entreprise, role=RoleUtilisateur.MEMBRE_PME)

    r = client.post(
        f"/entreprises/{entreprise.id}/kyc",
        files={"fichier": ("piece.pdf", b"contenu", "application/pdf")},
        headers=auth_headers(membre),
    )
    assert r.status_code == 422, r.text
