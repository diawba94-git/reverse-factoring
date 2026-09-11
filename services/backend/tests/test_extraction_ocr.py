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


def test_extraction_pre_remplit_dates_montants_et_lignes(client, db_session):
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)

    contenu = _construire_pdf(
        [
            "FACTURE N: FAC-TEST-001",
            "Date : 01/06/2026",
            "Echeance : 30/08/2026",
            "Prestation de conseil 2 500000",
            "Montant HT 3200000",
            "TVA 18%",
            "Montant TVA 576000",
            "Montant TTC 3776000",
        ]
    )

    reponse = client.post(
        "/factures/extraction-ocr",
        files={"fichier": ("facture.pdf", contenu, "application/pdf")},
        headers=auth_headers(membre),
    )

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["via_ocr"] is False
    assert corps["numero_facture"] == "FAC-TEST-001"
    assert corps["date_emission"] == "2026-06-01"
    assert corps["date_echeance"] == "2026-08-30"
    assert corps["taux_tva"] == "0.18"
    assert corps["montant_ht"] == "3200000"
    assert corps["montant_tva"] == "576000"
    assert corps["montant_ttc"] == "3776000"
    assert len(corps["lignes"]) == 1
    assert corps["lignes"][0]["designation"] == "Prestation de conseil"


def test_extraction_sans_champs_reconnaissables_retourne_brouillon_vide_sans_erreur(client, db_session):
    """Un PDF avec du texte natif (donc pas de bascule OCR) mais sans aucun champ de
    facture reconnaissable doit degrader proprement, jamais planter."""
    pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    membre = creer_utilisateur(db_session, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)

    contenu = _construire_pdf(["Ceci est un document quelconque sans rapport avec une facture."])

    reponse = client.post(
        "/factures/extraction-ocr",
        files={"fichier": ("sans-facture.pdf", contenu, "application/pdf")},
        headers=auth_headers(membre),
    )

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["via_ocr"] is False
    assert corps["numero_facture"] is None
    assert corps["lignes"] == []
    assert len(corps["avertissements"]) >= 1


def test_extraction_refusee_pour_un_role_non_autorise(client, db_session):
    donneur = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE)
    validateur = creer_utilisateur(db_session, entreprise=donneur, role=RoleUtilisateur.VALIDATEUR_1)

    reponse = client.post(
        "/factures/extraction-ocr",
        files={"fichier": ("facture.pdf", _construire_pdf(["FACTURE N: X"]), "application/pdf")},
        headers=auth_headers(validateur),
    )

    assert reponse.status_code == 403
