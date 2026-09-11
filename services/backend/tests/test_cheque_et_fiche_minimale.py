"""Le rendu PDF (WeasyPrint) exige des bibliotheques natives absentes de cet environnement
de dev (voir app/services/generation_facture_pdf.py) : ces tests monkeypatchent
generer_pdf_facture pour verifier la logique metier (statuts, cascade KYC, declaration de
cheque) independamment du rendu PDF lui-meme, deja hors de portee ici."""

import io
from datetime import date, timedelta
from decimal import Decimal

from app.models.enums import FormeJuridique, RoleUtilisateur, StatutFacture, StatutFiche, StatutKyc, TypeEntreprise

from .factories import auth_headers, creer_entreprise, creer_facture, creer_utilisateur


def _admin(db):
    entreprise_admin = creer_entreprise(db, type=TypeEntreprise.PME, raison_sociale="InvoiceUp Plateforme")
    return creer_utilisateur(db, entreprise=entreprise_admin, role=RoleUtilisateur.ADMIN)


def _sans_pdf(monkeypatch):
    monkeypatch.setattr("app.routers.factures.generer_pdf_facture", lambda *a, **k: b"%PDF-fake%")


def test_creation_fiche_minimale(client, db_session):
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME, raison_sociale="Sénégal Services SARL")
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)

    r = client.post(
        "/entreprises/fiche-minimale",
        json={
            "raison_sociale": "CFAO Distribution",
            "contact_invitation_nom": "Moussa Ndiaye",
            "contact_invitation_email": "moussa.ndiaye@cfao.sn",
        },
        headers=auth_headers(membre),
    )
    assert r.status_code == 201, r.text
    fiche = r.json()
    assert fiche["statut_fiche"] == "pre_inscrite"
    assert fiche["statut_kyc"] == "en_attente"
    assert fiche["ninea"] is None
    assert fiche["cree_par_entreprise_id"] == str(pme.id)
    assert fiche["contact_invitation_email"] == "moussa.ndiaye@cfao.sn"


def test_membre_pme_seul_ou_admin_peuvent_creer_une_fiche_minimale(client, db_session):
    donneur = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE)
    validateur = creer_utilisateur(db_session, entreprise=donneur, role=RoleUtilisateur.VALIDATEUR_1)

    r = client.post(
        "/entreprises/fiche-minimale",
        json={"raison_sociale": "X", "contact_invitation_nom": "Y", "contact_invitation_email": "y@x.sn"},
        headers=auth_headers(validateur),
    )
    assert r.status_code == 403


def test_transmission_vers_acheteur_pre_inscrit_bascule_en_attente_kyc(client, db_session, monkeypatch):
    _sans_pdf(monkeypatch)
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)
    acheteur_pre_inscrit = creer_entreprise(
        db_session,
        type=TypeEntreprise.GRANDE_ENTREPRISE,
        raison_sociale="CFAO Distribution",
        statut_fiche=StatutFiche.PRE_INSCRITE,
    )

    creation = client.post(
        "/factures/native",
        json={
            "donneur_ordre_id": str(acheteur_pre_inscrit.id),
            "date_emission": date.today().isoformat(),
            "date_echeance": (date.today() + timedelta(days=60)).isoformat(),
            "taux_tva": "0.18",
            "lignes": [{"designation": "Prestation", "quantite": "1", "prix_unitaire": "1000000"}],
        },
        headers=auth_headers(membre),
    )
    assert creation.status_code == 201, creation.text
    facture_id = creation.json()["id"]

    transmission = client.post(f"/factures/{facture_id}/transmettre", headers=auth_headers(membre))
    assert transmission.status_code == 200, transmission.text
    facture = transmission.json()
    assert facture["statut"] == "en_attente_kyc_acheteur"
    assert facture["numero_facture"] is not None


def test_validation_kyc_admin_debloque_les_factures_en_attente(client, db_session):
    admin = _admin(db_session)
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    acheteur = creer_entreprise(
        db_session,
        type=TypeEntreprise.GRANDE_ENTREPRISE,
        raison_sociale="CFAO Distribution 2",
        statut_fiche=StatutFiche.PRE_INSCRITE,
        statut_kyc=StatutKyc.EN_ATTENTE,
        forme_juridique=None,
    )
    facture_bloquee = creer_facture(db_session, pme=pme, donneur_ordre=acheteur, statut=StatutFacture.EN_ATTENTE_KYC_ACHETEUR)
    db_session.commit()

    # Complete les informations KYC minimales requises avant validation (voir doc §3.0quinquies.3)
    acheteur.forme_juridique = FormeJuridique.SARL
    acheteur.ninea = "998877665"
    acheteur.rccm = "SN.DKR.2026.B.9999"
    acheteur.kyc_document_url = "/uploads/kyc/x.pdf"
    db_session.commit()

    r = client.patch(
        f"/entreprises/{acheteur.id}/kyc",
        json={"statut_kyc": "valide"},
        headers=auth_headers(admin),
    )
    assert r.status_code == 200, r.text
    entreprise_out = r.json()
    assert entreprise_out["statut_fiche"] == "active"

    facture_apres = client.get(f"/factures/{facture_bloquee.id}", headers=auth_headers(admin))
    assert facture_apres.json()["statut"] == "emise"


def test_declaration_cheque_garantie(client, db_session):
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)
    donneur = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE)
    facture = creer_facture(db_session, pme=pme, donneur_ordre=donneur, duree_jours=60)
    db_session.commit()

    r = client.post(
        f"/factures/{facture.id}/cheque",
        params={
            "numero_cheque": "0041235",
            "banque_emettrice": "Banque Atlantique Sénégal",
            "date_encaissement_prevue": facture.date_echeance.isoformat(),
        },
        files={"fichier": ("cheque.jpg", io.BytesIO(b"fake-image-bytes"), "image/jpeg")},
        headers=auth_headers(membre),
    )
    assert r.status_code == 201, r.text
    cheque = r.json()
    assert cheque["statut"] == "declare"
    assert cheque["numero_cheque"] == "0041235"

    doublon = client.post(
        f"/factures/{facture.id}/cheque",
        params={
            "numero_cheque": "AUTRE",
            "banque_emettrice": "Autre banque",
            "date_encaissement_prevue": facture.date_echeance.isoformat(),
        },
        files={"fichier": ("cheque2.jpg", io.BytesIO(b"x"), "image/jpeg")},
        headers=auth_headers(membre),
    )
    assert doublon.status_code == 409


def test_declaration_cheque_refusee_si_date_incoherente(client, db_session):
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)
    donneur = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE)
    facture = creer_facture(db_session, pme=pme, donneur_ordre=donneur, duree_jours=60)
    db_session.commit()

    date_incoherente = facture.date_echeance + timedelta(days=90)
    r = client.post(
        f"/factures/{facture.id}/cheque",
        params={
            "numero_cheque": "0041235",
            "banque_emettrice": "Banque Atlantique Sénégal",
            "date_encaissement_prevue": date_incoherente.isoformat(),
        },
        files={"fichier": ("cheque.jpg", io.BytesIO(b"x"), "image/jpeg")},
        headers=auth_headers(membre),
    )
    assert r.status_code == 422
