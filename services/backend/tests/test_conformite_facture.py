from datetime import date, timedelta

from fpdf import FPDF

from app.models.enums import RoleUtilisateur, TypeEntreprise

from .factories import auth_headers, creer_entreprise, creer_utilisateur


def _construire_pdf(lignes: list[str]) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    for ligne in lignes:
        pdf.cell(0, 10, text=ligne, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def _setup(db, ninea_pme: str = "100200300"):
    pme = creer_entreprise(db, type=TypeEntreprise.PME, ninea=ninea_pme)
    donneur = creer_entreprise(db, type=TypeEntreprise.GRANDE_ENTREPRISE)
    membre = creer_utilisateur(db, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)
    return pme, donneur, membre


def _payload_form(donneur_id, numero="FAC-TEST-0001"):
    emission = date.today()
    return {
        "numero_facture": numero,
        "donneur_ordre_id": str(donneur_id),
        "date_emission": emission.isoformat(),
        "date_echeance": (emission + timedelta(days=60)).isoformat(),
        "devise": "FCFA",
    }


def _post_facture(client, donneur_id, membre, contenu_pdf, numero="FAC-TEST-0001"):
    return client.post(
        "/factures",
        data=_payload_form(donneur_id, numero),
        files={"fichier": ("facture.pdf", contenu_pdf, "application/pdf")},
        headers=auth_headers(membre),
    )


def test_pdf_sans_ninea_rejete(client, db_session):
    pme, donneur, membre = _setup(db_session)
    pdf = _construire_pdf(
        [
            "FACTURE N: FAC-TEST-0001",
            "MONTANT HT: 100 000 FCFA",
            "TVA 18%: 18 000 FCFA",
            "MONTANT TTC: 118 000 FCFA",
        ]
    )

    r = _post_facture(client, donneur.id, membre, pdf)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["statut"] == "rejetee_conformite"
    assert body["conformite_verifiee"] is True
    assert any("NINEA" in m for m in body["motifs_rejet_conformite"])


def test_pdf_ninea_different_rejete(client, db_session):
    pme, donneur, membre = _setup(db_session, ninea_pme="100200300")
    pdf = _construire_pdf(
        [
            "FACTURE N: FAC-TEST-0002",
            "NINEA: 999888777",
            "MONTANT HT: 100 000 FCFA",
            "TVA 18%: 18 000 FCFA",
            "MONTANT TTC: 118 000 FCFA",
        ]
    )

    r = _post_facture(client, donneur.id, membre, pdf, numero="FAC-TEST-0002")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["statut"] == "rejetee_conformite"
    assert any("ne correspond pas" in m for m in body["motifs_rejet_conformite"])


def test_pdf_montant_incoherent_rejete(client, db_session):
    pme, donneur, membre = _setup(db_session, ninea_pme="100200300")
    pdf = _construire_pdf(
        [
            "FACTURE N: FAC-TEST-0003",
            "NINEA: 100200300",
            "MONTANT HT: 100 000 FCFA",
            "TVA 18%: 50 000 FCFA",
            "MONTANT TTC: 150 000 FCFA",
        ]
    )

    r = _post_facture(client, donneur.id, membre, pdf, numero="FAC-TEST-0003")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["statut"] == "rejetee_conformite"
    assert any("incoherent" in m.lower() or "incohérent" in m.lower() for m in body["motifs_rejet_conformite"])


def test_pdf_conforme_passe_emise(client, db_session):
    pme, donneur, membre = _setup(db_session, ninea_pme="100200300")
    pdf = _construire_pdf(
        [
            "FACTURE N: FAC-TEST-0004",
            "NINEA: 100200300",
            "MONTANT HT: 100 000 FCFA",
            "TVA 18%: 18 000 FCFA",
            "MONTANT TTC: 118 000 FCFA",
            "CODE DE VALIDATION: ABC123XYZ",
        ]
    )

    r = _post_facture(client, donneur.id, membre, pdf, numero="FAC-TEST-0004")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["statut"] == "emise"
    assert body["conformite_verifiee"] is True
    assert body["motifs_rejet_conformite"] is None
    assert body["ninea_emetteur_extrait"] == "100200300"
    assert body["code_validation_dgid"] == "ABC123XYZ"
    assert body["montant_ht"] == "100000.00"
    assert body["montant_tva"] == "18000.00"
    assert body["montant_ttc"] == "118000.00"


def test_resoumission_apres_rejet_puis_conforme(client, db_session):
    pme, donneur, membre = _setup(db_session, ninea_pme="100200300")
    pdf_mauvais = _construire_pdf(["FACTURE N: FAC-TEST-0005", "MONTANT HT: 100 000 FCFA"])
    r1 = _post_facture(client, donneur.id, membre, pdf_mauvais, numero="FAC-TEST-0005")
    assert r1.status_code == 201, r1.text
    facture_id = r1.json()["id"]
    assert r1.json()["statut"] == "rejetee_conformite"

    pdf_bon = _construire_pdf(
        [
            "FACTURE N: FAC-TEST-0005",
            "NINEA: 100200300",
            "MONTANT HT: 100 000 FCFA",
            "TVA 18%: 18 000 FCFA",
            "MONTANT TTC: 118 000 FCFA",
        ]
    )
    r2 = client.post(
        f"/factures/{facture_id}/resoumettre",
        files={"fichier": ("facture.pdf", pdf_bon, "application/pdf")},
        headers=auth_headers(membre),
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["statut"] == "emise"
    assert r2.json()["motifs_rejet_conformite"] is None


def test_resoumission_refusee_si_facture_pas_rejetee_conformite(client, db_session):
    pme, donneur, membre = _setup(db_session, ninea_pme="100200300")
    pdf_bon = _construire_pdf(
        [
            "FACTURE N: FAC-TEST-0006",
            "NINEA: 100200300",
            "MONTANT HT: 100 000 FCFA",
            "TVA 18%: 18 000 FCFA",
            "MONTANT TTC: 118 000 FCFA",
        ]
    )
    r1 = _post_facture(client, donneur.id, membre, pdf_bon, numero="FAC-TEST-0006")
    facture_id = r1.json()["id"]
    assert r1.json()["statut"] == "emise"

    r2 = client.post(
        f"/factures/{facture_id}/resoumettre",
        files={"fichier": ("facture.pdf", pdf_bon, "application/pdf")},
        headers=auth_headers(membre),
    )
    assert r2.status_code == 400, r2.text
