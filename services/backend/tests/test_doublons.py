from app.models.enums import RoleUtilisateur, StatutFiche, TypeEntreprise

from .factories import auth_headers, creer_entreprise, creer_facture, creer_utilisateur


def _admin(db):
    entreprise_admin = creer_entreprise(db, type=TypeEntreprise.PME, raison_sociale="InvoiceUp Plateforme")
    return creer_utilisateur(db, entreprise=entreprise_admin, role=RoleUtilisateur.ADMIN)


def test_detecte_doublon_par_nom_et_telephone(client, db_session):
    admin = _admin(db_session)
    pme_creatrice = creer_entreprise(db_session, type=TypeEntreprise.PME, raison_sociale="ProxiCommerce")

    actif = creer_entreprise(
        db_session,
        type=TypeEntreprise.GRANDE_ENTREPRISE,
        raison_sociale="Auchan Senegal",
        contact_telephone="+221330000012",
        statut_fiche=StatutFiche.ACTIVE,
    )
    pre_inscrite = creer_entreprise(
        db_session,
        type=TypeEntreprise.GRANDE_ENTREPRISE,
        raison_sociale="Auchan SN SARL",
        contact_telephone="+221330000012",
        statut_fiche=StatutFiche.PRE_INSCRITE,
        cree_par_entreprise_id=pme_creatrice.id,
    )

    r = client.get("/admin/doublons/detecter", headers=auth_headers(admin))
    assert r.status_code == 200, r.text
    candidats = r.json()
    # La base de dev partagee peut deja contenir d'autres entreprises (seed/exploration
    # manuelle) : on verifie que NOTRE paire est bien detectee, pas le compte total.
    candidat = next(
        c for c in candidats if c["conserver"]["id"] == str(actif.id) and c["fusionner"]["id"] == str(pre_inscrite.id)
    )
    assert candidat["fusionner"]["cree_par"] == "ProxiCommerce"
    assert candidat["critere"] == "nom + telephone"
    assert candidat["score_similarite"] >= 0.9


def test_entreprises_dissemblables_non_detectees(client, db_session):
    admin = _admin(db_session)
    a = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE, raison_sociale="Zzqvorx Kimboto", contact_telephone="+221770000001")
    b = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE, raison_sociale="Plurifane Halsted", contact_telephone="+221770000002")

    r = client.get("/admin/doublons/detecter", headers=auth_headers(admin))
    assert r.status_code == 200, r.text
    paires = {(c["conserver"]["id"], c["fusionner"]["id"]) for c in r.json()}
    assert (str(a.id), str(b.id)) not in paires
    assert (str(b.id), str(a.id)) not in paires


def test_fusion_reassigne_factures_et_desactive_la_fiche_fusionnee(client, db_session):
    admin = _admin(db_session)
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME, raison_sociale="Batimat Senegal")
    conserver = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE, raison_sociale="APIX")
    fusionner = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE, raison_sociale="APIX SN")
    creer_facture(db_session, pme=pme, donneur_ordre=fusionner)
    db_session.commit()

    r = client.post(
        "/admin/doublons/fusionner",
        json={"conserver_id": str(conserver.id), "fusionner_id": str(fusionner.id)},
        headers=auth_headers(admin),
    )
    assert r.status_code == 200, r.text
    resultat = r.json()
    assert resultat["factures_reassignees"] == 1

    factures = client.get("/factures", params={"donneur_ordre_id": str(conserver.id)}, headers=auth_headers(admin))
    assert factures.status_code == 200, factures.text
    assert len(factures.json()) == 1

    entreprises = client.get("/entreprises", headers=auth_headers(admin)).json()
    fusionnee = next(e for e in entreprises if e["id"] == str(fusionner.id))
    assert fusionnee["actif"] is False


def test_fusion_refusee_si_deja_fusionnee(client, db_session):
    admin = _admin(db_session)
    conserver = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE, raison_sociale="CSE")
    fusionner = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE, raison_sociale="CSE bis", actif=False)

    r = client.post(
        "/admin/doublons/fusionner",
        json={"conserver_id": str(conserver.id), "fusionner_id": str(fusionner.id)},
        headers=auth_headers(admin),
    )
    assert r.status_code == 409, r.text
