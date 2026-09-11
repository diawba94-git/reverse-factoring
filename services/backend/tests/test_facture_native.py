from datetime import date, timedelta
from decimal import Decimal

import pdfplumber

from app.models.enums import RoleUtilisateur, TypeEntreprise

from .factories import auth_headers, creer_entreprise, creer_utilisateur


def _setup(db):
    pme = creer_entreprise(
        db,
        type=TypeEntreprise.PME,
        raison_sociale="Fournisseur Natif Test",
        adresse="10 Rue des Tests, Dakar",
    )
    donneur = creer_entreprise(
        db,
        type=TypeEntreprise.GRANDE_ENTREPRISE,
        raison_sociale="Acheteur Natif Test",
        adresse="20 Avenue des Tests, Dakar",
    )
    membre = creer_utilisateur(db, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)
    return pme, donneur, membre


def _valideurs(db, donneur):
    v1 = creer_utilisateur(db, entreprise=donneur, role=RoleUtilisateur.VALIDATEUR_1)
    v2 = creer_utilisateur(db, entreprise=donneur, role=RoleUtilisateur.VALIDATEUR_2)
    return v1, v2


def _payload_native(donneur_id, **overrides):
    emission = date.today()
    payload = {
        "donneur_ordre_id": str(donneur_id),
        "date_emission": emission.isoformat(),
        "date_echeance": (emission + timedelta(days=45)).isoformat(),
        "taux_tva": "0.18",
        "notes": "Paiement a reception.",
        "lignes": [
            {"designation": "Article A", "description": "Desc A", "quantite": "2", "prix_unitaire": "1000.00"},
            {"designation": "Article B", "description": "Desc B", "quantite": "1", "prix_unitaire": "500.00"},
            {"designation": "Article C", "description": None, "quantite": "3", "prix_unitaire": "200.00"},
        ],
    }
    payload.update(overrides)
    return payload


def test_facture_native_nait_brouillon_sans_numero(client, db_session):
    pme, donneur, membre = _setup(db_session)
    payload = _payload_native(donneur.id)

    r = client.post("/factures/native", json=payload, headers=auth_headers(membre))
    assert r.status_code == 201, r.text
    body = r.json()

    # 2*1000 + 1*500 + 3*200 = 3100
    assert body["montant_ht"] == "3100.00"
    assert body["montant_tva"] == "558.00"
    assert body["montant_ttc"] == "3658.00"
    assert body["statut"] == "brouillon"
    assert body["numero_facture"] is None
    assert body["source_creation"] == "creation_native"
    assert len(body["lignes"]) == 3
    assert sum(Decimal(l["montant_ligne"]) for l in body["lignes"]) == Decimal("3100.00")
    # Aucun numero saisi par l'utilisateur n'est accepte par le schema
    assert "numero_facture" not in payload


def test_transmission_attribue_le_numero_et_passe_emise_sans_conformite(client, db_session):
    pme, donneur, membre = _setup(db_session)
    r = client.post("/factures/native", json=_payload_native(donneur.id), headers=auth_headers(membre))
    facture_id = r.json()["id"]
    annee = date.today().year

    t = client.post(f"/factures/{facture_id}/transmettre", headers=auth_headers(membre))
    assert t.status_code == 200, t.text
    body = t.json()
    assert body["statut"] == "emise"
    assert body["numero_facture"] == f"FA-{annee}-0001"
    assert body["conformite_verifiee"] is False
    assert body["motifs_rejet_conformite"] is None


def test_pdf_genere_contient_infos_completes_des_deux_entreprises(client, db_session):
    pme, donneur, membre = _setup(db_session)
    payload = _payload_native(donneur.id)

    r = client.post("/factures/native", json=payload, headers=auth_headers(membre))
    assert r.status_code == 201, r.text
    url = r.json()["piece_justificative_url"]

    pdf_resp = client.get(url)
    assert pdf_resp.status_code == 200, pdf_resp.text

    import io

    with pdfplumber.open(io.BytesIO(pdf_resp.content)) as pdf:
        texte = "\n".join(page.extract_text() or "" for page in pdf.pages)

    # PME (emettrice) : pas seulement le nom
    assert pme.raison_sociale in texte
    assert pme.adresse in texte
    assert pme.contact_telephone in texte
    assert pme.contact_email in texte

    # Donneur d'ordre (destinataire) : pas seulement le nom
    assert donneur.raison_sociale in texte
    assert donneur.adresse in texte
    assert donneur.contact_telephone in texte
    assert donneur.contact_email in texte
    assert donneur.ninea in texte


def test_transmission_numerote_sans_trou_meme_apres_suppression_d_un_brouillon(client, db_session):
    pme, donneur, membre = _setup(db_session)
    annee = date.today().year
    headers = auth_headers(membre)

    r1 = client.post("/factures/native", json=_payload_native(donneur.id), headers=headers)
    r2 = client.post("/factures/native", json=_payload_native(donneur.id), headers=headers)
    r3 = client.post("/factures/native", json=_payload_native(donneur.id), headers=headers)
    ids = [r.json()["id"] for r in (r1, r2, r3)]

    # Le brouillon du milieu est supprime avant d'avoir jamais ete numerote : il ne doit
    # laisser aucun trou dans la sequence attribuee aux deux autres.
    d = client.delete(f"/factures/{ids[1]}", headers=headers)
    assert d.status_code == 204, d.text

    t1 = client.post(f"/factures/{ids[0]}/transmettre", headers=headers)
    t3 = client.post(f"/factures/{ids[2]}/transmettre", headers=headers)
    assert t1.json()["numero_facture"] == f"FA-{annee}-0001"
    assert t3.json()["numero_facture"] == f"FA-{annee}-0002"

    assert client.get(f"/factures/{ids[1]}", headers=headers).status_code == 404


def test_brouillon_ne_peut_pas_etre_transmis_deux_fois(client, db_session):
    pme, donneur, membre = _setup(db_session)
    headers = auth_headers(membre)
    r = client.post("/factures/native", json=_payload_native(donneur.id), headers=headers)
    facture_id = r.json()["id"]

    assert client.post(f"/factures/{facture_id}/transmettre", headers=headers).status_code == 200
    r2 = client.post(f"/factures/{facture_id}/transmettre", headers=headers)
    assert r2.status_code == 400, r2.text
    assert "brouillon" in r2.json()["detail"].lower()


def test_lignes_facture_native_modifiables_recalcule_totaux(client, db_session):
    pme, donneur, membre = _setup(db_session)
    r1 = client.post("/factures/native", json=_payload_native(donneur.id), headers=auth_headers(membre))
    facture_id = r1.json()["id"]
    lignes = r1.json()["lignes"]

    nouvelles_lignes = [
        {"id": lignes[0]["id"], "designation": "Article A modifie", "description": None, "quantite": "5", "prix_unitaire": "1000.00"},
        {"designation": "Nouvel article", "description": "Ajoute apres coup", "quantite": "1", "prix_unitaire": "2000.00"},
    ]
    r2 = client.patch(
        f"/factures/{facture_id}/lignes", json={"lignes": nouvelles_lignes}, headers=auth_headers(membre)
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert len(body["lignes"]) == 2
    assert body["montant_ht"] == "7000.00"


def test_brouillon_supprimable(client, db_session):
    pme, donneur, membre = _setup(db_session)
    headers = auth_headers(membre)
    r = client.post("/factures/native", json=_payload_native(donneur.id), headers=headers)
    facture_id = r.json()["id"]

    d = client.delete(f"/factures/{facture_id}", headers=headers)
    assert d.status_code == 204, d.text
    assert client.get(f"/factures/{facture_id}", headers=headers).status_code == 404


def test_facture_transmise_non_modifiable_et_non_supprimable(client, db_session):
    pme, donneur, membre = _setup(db_session)
    headers = auth_headers(membre)
    r1 = client.post("/factures/native", json=_payload_native(donneur.id), headers=headers)
    facture_id = r1.json()["id"]
    client.post(f"/factures/{facture_id}/transmettre", headers=headers)

    r2 = client.patch(
        f"/factures/{facture_id}/lignes",
        json={"lignes": [{"designation": "X", "quantite": "1", "prix_unitaire": "1"}]},
        headers=headers,
    )
    assert r2.status_code == 400, r2.text

    r3 = client.delete(f"/factures/{facture_id}", headers=headers)
    assert r3.status_code == 400, r3.text


def test_lignes_non_editables_apres_validation(client, db_session):
    pme, donneur, membre = _setup(db_session)
    headers = auth_headers(membre)
    r1 = client.post("/factures/native", json=_payload_native(donneur.id), headers=headers)
    facture_id = r1.json()["id"]
    client.post(f"/factures/{facture_id}/transmettre", headers=headers)

    v1, v2 = _valideurs(db_session, donneur)
    client.post(f"/factures/{facture_id}/valider", json={}, headers=auth_headers(v1))
    client.post(f"/factures/{facture_id}/valider", json={}, headers=auth_headers(v2))

    r2 = client.patch(
        f"/factures/{facture_id}/lignes",
        json={"lignes": [{"designation": "X", "quantite": "1", "prix_unitaire": "1"}]},
        headers=headers,
    )
    assert r2.status_code == 400, r2.text
