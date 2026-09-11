from app.models.enums import RoleUtilisateur, TypeEntreprise

from .factories import auth_headers, creer_entreprise, creer_facture, creer_utilisateur


def test_lister_factures_sans_pagination_retourne_tout_sans_entete(client, db_session):
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    donneur = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE)
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)
    for _ in range(3):
        creer_facture(db_session, pme=pme, donneur_ordre=donneur)
    db_session.commit()

    r = client.get("/factures", headers=auth_headers(membre))
    assert r.status_code == 200
    assert len(r.json()) == 3
    assert "x-total-count" not in {k.lower() for k in r.headers.keys()}


def test_lister_factures_avec_pagination_decoupe_et_expose_le_total(client, db_session):
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    donneur = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE)
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)
    for _ in range(5):
        creer_facture(db_session, pme=pme, donneur_ordre=donneur)
    db_session.commit()

    r = client.get("/factures?page=1&per_page=2", headers=auth_headers(membre))
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert r.headers.get("x-total-count") == "5"

    r2 = client.get("/factures?page=3&per_page=2", headers=auth_headers(membre))
    assert len(r2.json()) == 1
    assert r2.headers.get("x-total-count") == "5"
