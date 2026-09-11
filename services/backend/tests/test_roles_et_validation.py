from decimal import Decimal

from app.models.enums import RoleUtilisateur, StatutFacture, StatutKyc, TypeEntreprise

from .factories import auth_headers, creer_entreprise, creer_facture, creer_utilisateur


def _setup_facture(db, montant=Decimal("100000")):
    pme = creer_entreprise(db, type=TypeEntreprise.PME)
    donneur = creer_entreprise(db, type=TypeEntreprise.GRANDE_ENTREPRISE)
    facture = creer_facture(db, pme=pme, donneur_ordre=donneur, montant=montant)
    return pme, donneur, facture


def test_deux_validations_du_meme_role_ne_valident_jamais_la_facture(client, db_session):
    """Deux validateur_1 differents (comptes distincts) ne suffisent jamais : il faut un
    validateur_1 ET un validateur_2, quel que soit le montant (pas de seuil)."""
    pme, donneur, facture = _setup_facture(db_session, montant=Decimal("50000000"))
    validateur_1_a = creer_utilisateur(db_session, entreprise=donneur, role=RoleUtilisateur.VALIDATEUR_1)
    validateur_1_b = creer_utilisateur(db_session, entreprise=donneur, role=RoleUtilisateur.VALIDATEUR_1)

    r1 = client.post(f"/factures/{facture.id}/valider", json={}, headers=auth_headers(validateur_1_a))
    assert r1.status_code == 200, r1.text
    assert r1.json()["statut"] == "validation_complementaire_requise"

    r2 = client.post(f"/factures/{facture.id}/valider", json={}, headers=auth_headers(validateur_1_b))
    assert r2.status_code == 400, r2.text

    r3 = client.get(f"/factures/{facture.id}", headers=auth_headers(validateur_1_a))
    assert r3.json()["statut"] == "validation_complementaire_requise"
    assert r3.json()["statut"] != "validee"


def test_validation_complementaire_avec_roles_differents_valide_la_facture_dans_les_deux_ordres(client, db_session):
    # Ordre 1 : validateur_1 puis validateur_2
    pme, donneur, facture = _setup_facture(db_session)
    v1 = creer_utilisateur(db_session, entreprise=donneur, role=RoleUtilisateur.VALIDATEUR_1)
    v2 = creer_utilisateur(db_session, entreprise=donneur, role=RoleUtilisateur.VALIDATEUR_2)

    r1 = client.post(f"/factures/{facture.id}/valider", json={}, headers=auth_headers(v1))
    assert r1.json()["statut"] == "validation_complementaire_requise"
    assert r1.json()["premiere_validation"]["role_validateur"] == "validateur_1"

    r2 = client.post(f"/factures/{facture.id}/valider", json={}, headers=auth_headers(v2))
    assert r2.status_code == 200, r2.text
    assert r2.json()["statut"] == "validee"

    # Ordre 2 : validateur_2 puis validateur_1, sur une autre facture
    _, donneur2, facture2 = _setup_facture(db_session)
    v1b = creer_utilisateur(db_session, entreprise=donneur2, role=RoleUtilisateur.VALIDATEUR_1)
    v2b = creer_utilisateur(db_session, entreprise=donneur2, role=RoleUtilisateur.VALIDATEUR_2)

    r3 = client.post(f"/factures/{facture2.id}/valider", json={}, headers=auth_headers(v2b))
    assert r3.json()["statut"] == "validation_complementaire_requise"
    assert r3.json()["premiere_validation"]["role_validateur"] == "validateur_2"

    r4 = client.post(f"/factures/{facture2.id}/valider", json={}, headers=auth_headers(v1b))
    assert r4.status_code == 200, r4.text
    assert r4.json()["statut"] == "validee"


def test_membre_pme_ne_peut_jamais_valider_une_facture(client, db_session):
    pme, donneur, facture = _setup_facture(db_session)
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)

    r = client.post(f"/factures/{facture.id}/valider", json={}, headers=auth_headers(membre))
    assert r.status_code == 403, r.text


def test_pme_ne_peut_pas_inviter_avec_role_validateur_1(client, db_session):
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME, statut_kyc=StatutKyc.VALIDE)
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)

    r = client.post(
        f"/entreprises/{pme.id}/inviter",
        json={
            "telephone": "+221709998877",
            "email": "collegue@example.sn",
            "nom": "Collegue Test",
            "role": "validateur_1",
        },
        headers=auth_headers(membre),
    )
    assert r.status_code == 403, r.text


def test_compte_non_kyc_valide_ne_peut_pas_inviter(client, db_session):
    donneur = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE, statut_kyc=StatutKyc.EN_ATTENTE)
    v1 = creer_utilisateur(db_session, entreprise=donneur, role=RoleUtilisateur.VALIDATEUR_1)

    r = client.post(
        f"/entreprises/{donneur.id}/inviter",
        json={
            "telephone": "+221709997766",
            "email": "collegue@example.sn",
            "nom": "Collegue Test",
            "role": "validateur_2",
        },
        headers=auth_headers(v1),
    )
    assert r.status_code == 403, r.text


def test_invitation_reussie_puis_acceptation_active_le_compte(client, db_session):
    donneur = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE, statut_kyc=StatutKyc.VALIDE)
    v1 = creer_utilisateur(db_session, entreprise=donneur, role=RoleUtilisateur.VALIDATEUR_1)

    r = client.post(
        f"/entreprises/{donneur.id}/inviter",
        json={
            "telephone": "+221709996655",
            "email": "collegue@example.sn",
            "nom": "Collegue Test",
            "role": "validateur_2",
        },
        headers=auth_headers(v1),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["role"] == "validateur_2"
    assert body["entreprise_id"] == str(donneur.id)

    accept = client.post(
        f"/auth/accepter-invitation/{body['token']}",
        json={"mot_de_passe": "NouveauMotDePasse123!"},
    )
    assert accept.status_code == 200, accept.text
    assert accept.json()["access_token"]

    login = client.post(
        "/auth/login",
        json={"telephone": "+221709996655", "mot_de_passe": "NouveauMotDePasse123!"},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]
