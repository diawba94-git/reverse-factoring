from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.calcul_frais import DureeInsuffisanteError, TaegDepasseError, calculer_frais

UN_TIERS = Decimal(1) / Decimal(3)
DEUX_TIERS = Decimal(2) / Decimal(3)


def _grille(**overrides):
    defaults = dict(
        taux_total_minimum=Decimal("0.023"),
        taux_total_maximum=Decimal("0.03"),
        proportion_cedra=UN_TIERS,
        proportion_partenaire=DEUX_TIERS,
        plafond_montant=None,
        duree_minimum_jours=60,
        duree_maximum_jours=90,
        taux_avance=Decimal("0.80"),
        type_partenaire="banque",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_calcul_nominal_90_jours():
    """Exemple chiffre du doc §6.4 : facture de 3 000 000 FCFA a 90 jours."""
    resultat = calculer_frais(Decimal("3000000"), 90, _grille())

    assert resultat.montant_avance_initial == Decimal("2400000.00")
    assert resultat.part_plateforme == Decimal("30000.00")
    assert resultat.part_partenaire == Decimal("60000.00")
    assert resultat.frais_total == Decimal("90000.00")
    assert resultat.montant_solde_du == Decimal("510000.00")
    assert resultat.taeg_annualise == Decimal("0.1217")


def test_calcul_nominal_60_jours():
    """Meme facture a 60 jours (borne basse du bareme degressif, doc §6.4)."""
    resultat = calculer_frais(Decimal("3000000"), 60, _grille())

    assert resultat.part_plateforme == Decimal("23000.00")
    assert resultat.part_partenaire == Decimal("46000.00")
    assert resultat.frais_total == Decimal("69000.00")
    assert resultat.montant_solde_du == Decimal("531000.00")
    assert resultat.taeg_annualise == Decimal("0.1399")
    assert resultat.taeg_annualise < Decimal("0.14")


def test_taux_total_interpole_lineairement_entre_les_bornes():
    resultat_75j = calculer_frais(Decimal("3000000"), 75, _grille())
    # A mi-chemin de la fenetre 60-90j, le taux total doit etre a mi-chemin de 2,3%-3%.
    assert resultat_75j.taux_total_applique == Decimal("0.0265")


def test_frais_plafonnes_par_plafond_montant():
    grille = _grille(plafond_montant=Decimal("20000"))
    resultat = calculer_frais(Decimal("3000000"), 90, grille)

    assert resultat.part_plateforme == Decimal("20000.00")
    assert resultat.frais_total == Decimal("20000.00") + resultat.part_partenaire


def test_duree_sous_le_minimum_leve_exception():
    with pytest.raises(DureeInsuffisanteError):
        calculer_frais(Decimal("1000000"), 30, _grille())


def test_duree_au_dela_du_maximum_leve_exception():
    with pytest.raises(DureeInsuffisanteError):
        calculer_frais(Decimal("1000000"), 120, _grille())


def test_taeg_trop_eleve_leve_exception_non_desactivable():
    grille = _grille(taux_total_minimum=Decimal("0.10"), taux_total_maximum=Decimal("0.10"))
    with pytest.raises(TaegDepasseError):
        calculer_frais(Decimal("1000000"), 60, grille)


def test_plafond_legal_plus_haut_pour_une_imf():
    """Un taux qui depasserait le plafond banque (14%) peut rester conforme pour une IMF (24%)."""
    grille = _grille(
        taux_total_minimum=Decimal("0.035"), taux_total_maximum=Decimal("0.035"), type_partenaire="imf"
    )
    resultat = calculer_frais(Decimal("1000000"), 60, grille)
    assert Decimal("0.14") < resultat.taeg_annualise < Decimal("0.24")


def test_repartition_partenaire_plateforme_egale_frais_total():
    resultat = calculer_frais(Decimal("1000000"), 60, _grille())
    assert resultat.part_partenaire + resultat.part_plateforme == resultat.frais_total
