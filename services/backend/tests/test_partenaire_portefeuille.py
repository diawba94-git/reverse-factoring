from decimal import Decimal

from app.models.avance import Avance
from app.models.enums import MethodeVersement, RoleUtilisateur, StatutAvance, StatutFacture, TypeEntreprise, TypeLimite
from app.models.limite_credit import LimiteCredit
from app.models.remboursement import Remboursement

from .factories import auth_headers, creer_entreprise, creer_facture, creer_grille_active, creer_utilisateur


def _setup_avance_versee(db):
    pme = creer_entreprise(db, type=TypeEntreprise.PME)
    pme.secteur_activite = "Agroalimentaire"
    donneur = creer_entreprise(db, type=TypeEntreprise.GRANDE_ENTREPRISE)
    donneur.secteur_activite = "Distribution"
    partenaire = creer_entreprise(db, type=TypeEntreprise.PARTENAIRE_FINANCIER)
    agent = creer_utilisateur(db, entreprise=partenaire, role=RoleUtilisateur.AGENT_FINANCIER)
    grille = creer_grille_active(db)
    facture = creer_facture(db, pme=pme, donneur_ordre=donneur, montant=Decimal("10000000"), statut=StatutFacture.VALIDEE)

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
    db.add(avance)
    db.flush()

    limite = LimiteCredit(
        partenaire_financier_id=partenaire.id,
        entreprise_cible_id=donneur.id,
        type_limite=TypeLimite.ACHETEUR,
        montant_plafond=Decimal("50000000"),
        montant_utilise=Decimal("8000000"),
    )
    db.add(limite)
    db.commit()

    return pme, donneur, partenaire, agent, facture, avance


def test_portefeuille_par_donneur_ordre_agrege_encours_et_limite(client, db_session):
    pme, donneur, partenaire, agent, facture, avance = _setup_avance_versee(db_session)

    r = client.get("/partenaire/portefeuille", headers=auth_headers(agent))
    assert r.status_code == 200, r.text
    corps = r.json()
    assert len(corps) == 1
    assert corps[0]["donneur_ordre_id"] == str(donneur.id)
    assert corps[0]["encours"] == "1770000.00"
    assert corps[0]["limite_plafond"] == "50000000.00"
    assert corps[0]["limite_utilisee"] == "8000000.00"
    assert corps[0]["retards"] == 0


def test_pme_financees_agrege_encours_et_nombre_factures(client, db_session):
    pme, donneur, partenaire, agent, facture, avance = _setup_avance_versee(db_session)

    r = client.get("/partenaire/pme-financees", headers=auth_headers(agent))
    assert r.status_code == 200, r.text
    corps = r.json()
    assert len(corps) == 1
    assert corps[0]["pme_id"] == str(pme.id)
    assert corps[0]["nombre_factures"] == 1
    assert corps[0]["encours"] == "1770000.00"


def test_acheteurs_partenaires_inclut_secteur_et_taux_retard(client, db_session):
    pme, donneur, partenaire, agent, facture, avance = _setup_avance_versee(db_session)

    r = client.get("/partenaire/acheteurs", headers=auth_headers(agent))
    assert r.status_code == 200, r.text
    corps = r.json()
    assert len(corps) == 1
    assert corps[0]["secteur_activite"] == "Distribution"
    assert corps[0]["taux_retard"] == "0.0"


def test_remboursements_du_partenaire_scoped_a_ses_avances(client, db_session):
    pme, donneur, partenaire, agent, facture, avance = _setup_avance_versee(db_session)
    remboursement = Remboursement(
        avance_id=avance.id,
        montant_recu=Decimal("1770000"),
        date_reception=facture.date_echeance,
        source_entreprise_id=donneur.id,
    )
    db_session.add(remboursement)
    db_session.commit()

    r = client.get("/partenaire/remboursements", headers=auth_headers(agent))
    assert r.status_code == 200, r.text
    corps = r.json()
    assert len(corps) == 1
    assert corps[0]["source_entreprise"] == donneur.raison_sociale
    assert corps[0]["ecart"] == "0.00"


def test_conventions_scope_relations_aux_avances_du_partenaire(client, db_session):
    pme, donneur, partenaire, agent, facture, avance = _setup_avance_versee(db_session)
    autre_pme = creer_entreprise(db_session, type=TypeEntreprise.PME)
    autre_donneur = creer_entreprise(db_session, type=TypeEntreprise.GRANDE_ENTREPRISE)
    from app.models.relation_pme_donneur_ordre import RelationPmeDonneurOrdre

    db_session.add(RelationPmeDonneurOrdre(pme_id=pme.id, donneur_ordre_id=donneur.id))
    db_session.add(RelationPmeDonneurOrdre(pme_id=autre_pme.id, donneur_ordre_id=autre_donneur.id))
    db_session.commit()

    r = client.get("/relations", headers=auth_headers(agent))
    assert r.status_code == 200, r.text
    corps = r.json()
    assert len(corps) == 1
    assert corps[0]["pme_id"] == str(pme.id)
    assert corps[0]["donneur_ordre_id"] == str(donneur.id)
