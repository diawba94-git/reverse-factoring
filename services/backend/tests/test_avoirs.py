from decimal import Decimal

from app.models.avance import Avance
from app.models.avoir_facture import AvoirFacture
from app.models.creance_compensation import CreanceCompensation
from app.models.enums import (
    MethodeVersement,
    MotifAvoir,
    RoleUtilisateur,
    StatutAvance,
    StatutAvoir,
    StatutCreance,
    StatutFacture,
    TypeEntreprise,
)

from .factories import auth_headers, creer_entreprise, creer_facture, creer_grille_active, creer_utilisateur


def _setup_pme_et_acheteur(db):
    pme = creer_entreprise(db, type=TypeEntreprise.PME)
    donneur = creer_entreprise(db, type=TypeEntreprise.GRANDE_ENTREPRISE)
    membre = creer_utilisateur(db, entreprise=pme, role=RoleUtilisateur.MEMBRE_PME)
    validateur = creer_utilisateur(db, entreprise=donneur, role=RoleUtilisateur.VALIDATEUR_1)
    return pme, donneur, membre, validateur


def _avoir_payload(montant_ttc: str) -> dict:
    montant_ttc_dec = Decimal(montant_ttc)
    montant_ht = (montant_ttc_dec / Decimal("1.18")).quantize(Decimal("0.01"))
    montant_tva = montant_ttc_dec - montant_ht
    return {
        "montant_ht": str(montant_ht),
        "montant_tva": str(montant_tva),
        "montant_ttc": str(montant_ttc_dec),
        "motif": "remise_commerciale",
    }


def test_avoir_sur_facture_non_avancee_reduit_montant_facture(db_session, client):
    pme, donneur, membre, validateur = _setup_pme_et_acheteur(db_session)
    facture = creer_facture(db_session, pme=pme, donneur_ordre=donneur, montant=Decimal("1000000"), statut=StatutFacture.VALIDEE)
    db_session.commit()

    r = client.post(f"/factures/{facture.id}/avoirs", json=_avoir_payload("100000"), headers=auth_headers(membre))
    assert r.status_code == 201, r.text
    avoir_id = r.json()["id"]
    assert r.json()["numero_avoir"].startswith("AV-")
    assert r.json()["statut"] == "emis"

    r2 = client.post(f"/avoirs/{avoir_id}/confirmer", headers=auth_headers(validateur))
    assert r2.status_code == 200, r2.text
    assert r2.json()["statut"] == "confirme_par_acheteur"
    assert r2.json()["effet_applique"] == "montant_facture_reduit"

    db_session.refresh(facture)
    assert facture.montant_ttc == Decimal("900000.00")
    assert db_session.query(CreanceCompensation).count() == 0


def test_avoir_sur_facture_avancee_ecart_couvert_par_solde(db_session, client):
    pme, donneur, membre, validateur = _setup_pme_et_acheteur(db_session)
    partenaire = creer_entreprise(db_session, type=TypeEntreprise.PARTENAIRE_FINANCIER)
    grille = creer_grille_active(db_session)
    facture = creer_facture(db_session, pme=pme, donneur_ordre=donneur, montant=Decimal("10000000"), statut=StatutFacture.AVANCE_VERSEE)
    avance = Avance(
        facture_id=facture.id,
        partenaire_financier_id=partenaire.id,
        grille_tarifaire_id=grille.id,
        montant_avance_initial=Decimal("8000000"),
        frais_total=Decimal("230000"),
        montant_solde_du=Decimal("1770000"),
        part_partenaire=Decimal("153300"),
        part_plateforme=Decimal("76700"),
        taeg_annualise=Decimal("0.1399"),
        statut=StatutAvance.AVANCE_VERSEE,
        methode_versement=MethodeVersement.WAVE,
        garantie_detenue_avant_financement=False,
    )
    db_session.add(avance)
    db_session.commit()

    r = client.post(f"/factures/{facture.id}/avoirs", json=_avoir_payload("500000"), headers=auth_headers(membre))
    assert r.status_code == 201, r.text
    avoir_id = r.json()["id"]

    r2 = client.post(f"/avoirs/{avoir_id}/confirmer", headers=auth_headers(validateur))
    assert r2.status_code == 200, r2.text
    assert r2.json()["effet_applique"] == "solde_reduit"

    db_session.refresh(avance)
    assert avance.montant_solde_du == Decimal("1270000.00")
    assert db_session.query(CreanceCompensation).count() == 0


def test_avoir_sur_facture_avancee_ecart_depasse_solde_cree_creance_pour_reliquat_exact(db_session, client):
    pme, donneur, membre, validateur = _setup_pme_et_acheteur(db_session)
    partenaire = creer_entreprise(db_session, type=TypeEntreprise.PARTENAIRE_FINANCIER)
    grille = creer_grille_active(db_session)
    facture = creer_facture(db_session, pme=pme, donneur_ordre=donneur, montant=Decimal("10000000"), statut=StatutFacture.AVANCE_VERSEE)
    avance = Avance(
        facture_id=facture.id,
        partenaire_financier_id=partenaire.id,
        grille_tarifaire_id=grille.id,
        montant_avance_initial=Decimal("8000000"),
        frais_total=Decimal("230000"),
        montant_solde_du=Decimal("1770000"),
        part_partenaire=Decimal("153300"),
        part_plateforme=Decimal("76700"),
        taeg_annualise=Decimal("0.1399"),
        statut=StatutAvance.AVANCE_VERSEE,
        methode_versement=MethodeVersement.WAVE,
        garantie_detenue_avant_financement=False,
    )
    db_session.add(avance)
    db_session.commit()

    r = client.post(f"/factures/{facture.id}/avoirs", json=_avoir_payload("2000000"), headers=auth_headers(membre))
    assert r.status_code == 201, r.text
    avoir_id = r.json()["id"]

    r2 = client.post(f"/avoirs/{avoir_id}/confirmer", headers=auth_headers(validateur))
    assert r2.status_code == 200, r2.text
    assert r2.json()["effet_applique"] == "creance_creee"

    db_session.refresh(avance)
    assert avance.montant_solde_du == Decimal("0.00")

    creance = db_session.query(CreanceCompensation).filter(CreanceCompensation.avoir_id == avoir_id).first()
    assert creance is not None
    assert creance.montant_du == Decimal("230000.00")  # 2 000 000 - 1 770 000
    assert creance.montant_recouvre == Decimal("0")
    assert creance.statut == StatutCreance.EN_ATTENTE
    assert creance.pme_id == pme.id


def test_nouvelle_avance_deduit_automatiquement_creance_en_attente_avant_versement(db_session, client):
    pme, donneur, membre, validateur = _setup_pme_et_acheteur(db_session)
    autre_donneur = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE)
    partenaire = creer_entreprise(db_session, type=TypeEntreprise.PARTENAIRE_FINANCIER)
    creer_grille_active(db_session)

    facture_source = creer_facture(db_session, pme=pme, donneur_ordre=donneur, montant=Decimal("1000000"), statut=StatutFacture.VALIDEE)

    # Cree l'avoir via l'ORM directement (pas besoin de repasser par l'API pour ce fixture),
    # puis la creance associee, comme le ferait confirmer_avoir sur une facture avancee.
    avoir_source = AvoirFacture(
        numero_avoir="AV-2026-0001",
        facture_id=facture_source.id,
        montant_ht=Decimal("84745.76"),
        montant_tva=Decimal("15254.24"),
        montant_ttc=Decimal("100000.00"),
        motif=MotifAvoir.AUTRE,
        statut=StatutAvoir.CONFIRME_PAR_ACHETEUR,
        date_emission=facture_source.date_emission,
        effet_applique="creance_creee",
    )
    db_session.add(avoir_source)
    db_session.flush()
    creance = CreanceCompensation(
        pme_id=pme.id,
        avoir_id=avoir_source.id,
        montant_du=Decimal("100000"),
        montant_recouvre=Decimal("0"),
        statut=StatutCreance.EN_ATTENTE,
    )
    db_session.add(creance)
    db_session.commit()

    # Nouvelle facture, donneur d'ordre DIFFERENT de celui de l'avoir d'origine.
    facture_nouvelle = creer_facture(db_session, pme=pme, donneur_ordre=autre_donneur, montant=Decimal("5000000"), statut=StatutFacture.VALIDEE)
    db_session.commit()

    r = client.post(
        "/avances",
        json={"facture_id": str(facture_nouvelle.id), "partenaire_financier_id": str(partenaire.id), "methode_versement": "wave"},
        headers=auth_headers(membre),
    )
    assert r.status_code == 201, r.text
    corps = r.json()
    # 80% de 5 000 000 = 4 000 000, moins la creance de 100 000 deduite en priorite.
    assert corps["montant_avance_initial"] == "3900000.00"

    db_session.refresh(creance)
    assert creance.statut == StatutCreance.SOLDEE
    assert creance.montant_recouvre == Decimal("100000.00")


def test_avoir_rejete_par_acheteur_annule_effet_deja_applique(db_session, client):
    pme, donneur, membre, validateur = _setup_pme_et_acheteur(db_session)
    facture = creer_facture(db_session, pme=pme, donneur_ordre=donneur, montant=Decimal("1000000"), statut=StatutFacture.VALIDEE)
    db_session.commit()

    r = client.post(f"/factures/{facture.id}/avoirs", json=_avoir_payload("150000"), headers=auth_headers(membre))
    avoir_id = r.json()["id"]
    client.post(f"/avoirs/{avoir_id}/confirmer", headers=auth_headers(validateur))
    db_session.refresh(facture)
    assert facture.montant_ttc == Decimal("850000.00")

    r2 = client.post(f"/avoirs/{avoir_id}/rejeter", headers=auth_headers(validateur))
    assert r2.status_code == 200, r2.text
    assert r2.json()["statut"] == "rejete"
    assert r2.json()["effet_applique"] is None

    db_session.refresh(facture)
    assert facture.montant_ttc == Decimal("1000000.00")


def test_avoir_rejete_apres_creance_creee_restaure_solde_et_supprime_la_creance(db_session, client):
    pme, donneur, membre, validateur = _setup_pme_et_acheteur(db_session)
    partenaire = creer_entreprise(db_session, type=TypeEntreprise.PARTENAIRE_FINANCIER)
    grille = creer_grille_active(db_session)
    facture = creer_facture(db_session, pme=pme, donneur_ordre=donneur, montant=Decimal("10000000"), statut=StatutFacture.AVANCE_VERSEE)
    avance = Avance(
        facture_id=facture.id,
        partenaire_financier_id=partenaire.id,
        grille_tarifaire_id=grille.id,
        montant_avance_initial=Decimal("8000000"),
        frais_total=Decimal("230000"),
        montant_solde_du=Decimal("1770000"),
        part_partenaire=Decimal("153300"),
        part_plateforme=Decimal("76700"),
        taeg_annualise=Decimal("0.1399"),
        statut=StatutAvance.AVANCE_VERSEE,
        methode_versement=MethodeVersement.WAVE,
        garantie_detenue_avant_financement=False,
    )
    db_session.add(avance)
    db_session.commit()

    r = client.post(f"/factures/{facture.id}/avoirs", json=_avoir_payload("2000000"), headers=auth_headers(membre))
    avoir_id = r.json()["id"]
    client.post(f"/avoirs/{avoir_id}/confirmer", headers=auth_headers(validateur))
    db_session.refresh(avance)
    assert avance.montant_solde_du == Decimal("0.00")
    assert db_session.query(CreanceCompensation).filter(CreanceCompensation.avoir_id == avoir_id).count() == 1

    r2 = client.post(f"/avoirs/{avoir_id}/rejeter", headers=auth_headers(validateur))
    assert r2.status_code == 200, r2.text

    db_session.refresh(avance)
    assert avance.montant_solde_du == Decimal("1770000.00")
    assert db_session.query(CreanceCompensation).filter(CreanceCompensation.avoir_id == avoir_id).count() == 0


def test_membre_pme_ne_peut_jamais_confirmer_ni_rejeter_un_avoir(db_session, client):
    pme, donneur, membre, validateur = _setup_pme_et_acheteur(db_session)
    facture = creer_facture(db_session, pme=pme, donneur_ordre=donneur, montant=Decimal("1000000"), statut=StatutFacture.VALIDEE)
    db_session.commit()

    r = client.post(f"/factures/{facture.id}/avoirs", json=_avoir_payload("100000"), headers=auth_headers(membre))
    avoir_id = r.json()["id"]

    r2 = client.post(f"/avoirs/{avoir_id}/confirmer", headers=auth_headers(membre))
    assert r2.status_code == 403

    r3 = client.post(f"/avoirs/{avoir_id}/rejeter", headers=auth_headers(membre))
    assert r3.status_code == 403


def test_validateur_d_une_autre_entreprise_ne_peut_pas_confirmer_ni_rejeter(db_session, client):
    pme, donneur, membre, validateur = _setup_pme_et_acheteur(db_session)
    autre_entreprise = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE)
    autre_validateur = creer_utilisateur(db_session, entreprise=autre_entreprise, role=RoleUtilisateur.VALIDATEUR_1)
    facture = creer_facture(db_session, pme=pme, donneur_ordre=donneur, montant=Decimal("1000000"), statut=StatutFacture.VALIDEE)
    db_session.commit()

    r = client.post(f"/factures/{facture.id}/avoirs", json=_avoir_payload("100000"), headers=auth_headers(membre))
    avoir_id = r.json()["id"]

    r2 = client.post(f"/avoirs/{avoir_id}/confirmer", headers=auth_headers(autre_validateur))
    assert r2.status_code == 403

    r3 = client.post(f"/avoirs/{avoir_id}/rejeter", headers=auth_headers(autre_validateur))
    assert r3.status_code == 403


def test_creation_avoir_refusee_si_montant_depasse_le_restant_du(db_session, client):
    pme, donneur, membre, validateur = _setup_pme_et_acheteur(db_session)
    facture = creer_facture(db_session, pme=pme, donneur_ordre=donneur, montant=Decimal("1000000"), statut=StatutFacture.VALIDEE)
    db_session.commit()

    r = client.post(f"/factures/{facture.id}/avoirs", json=_avoir_payload("1500000"), headers=auth_headers(membre))
    assert r.status_code == 422
    assert "depasse" in r.json()["detail"]


def test_numerotation_avoirs_est_sequentielle_par_pme(db_session, client):
    pme, donneur, membre, validateur = _setup_pme_et_acheteur(db_session)
    facture1 = creer_facture(db_session, pme=pme, donneur_ordre=donneur, montant=Decimal("1000000"), statut=StatutFacture.VALIDEE)
    facture2 = creer_facture(db_session, pme=pme, donneur_ordre=donneur, montant=Decimal("1000000"), statut=StatutFacture.VALIDEE)
    db_session.commit()

    r1 = client.post(f"/factures/{facture1.id}/avoirs", json=_avoir_payload("50000"), headers=auth_headers(membre))
    r2 = client.post(f"/factures/{facture2.id}/avoirs", json=_avoir_payload("50000"), headers=auth_headers(membre))
    n1, n2 = r1.json()["numero_avoir"], r2.json()["numero_avoir"]
    prefixe = n1.rsplit("-", 1)[0]
    assert n2 == f"{prefixe}-{int(n1.rsplit('-', 1)[1]) + 1:0{len(n1.rsplit('-', 1)[1])}d}"
