"""Service de calcul des frais d'avance sur facture.

Isole toute la logique metier de tarification des routes API, pour rester testable
independamment (voir tests/test_calcul_frais.py). Implemente le bareme degressif du
doc §6.1bis/6.2 : le taux total interpole lineairement selon la duree entre
taux_total_minimum et taux_total_maximum, puis se repartit entre Cedra
(proportion_cedra) et le partenaire (proportion_partenaire).
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

JOURS_ANNEE = Decimal("365")
PLAFOND_TAEG_BANQUE = Decimal("0.14")
PLAFOND_TAEG_IMF = Decimal("0.24")

TWO_PLACES = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")


class DureeInsuffisanteError(Exception):
    """Levee quand la duree de la facture est hors de la fenetre eligible de la grille
    (sous duree_minimum_jours ou au-dela de duree_maximum_jours)."""


class TaegDepasseError(Exception):
    """Garde-fou non desactivable : le TAEG annualise ne doit jamais depasser le plafond
    legal du type de partenaire (14% banque / 24% IMF), meme si le bareme degressif est
    en theorie deja conforme par construction."""


@dataclass(frozen=True)
class ResultatCalculFrais:
    montant_avance_initial: Decimal
    montant_solde_du: Decimal
    frais_total: Decimal
    taux_total_applique: Decimal
    taeg_annualise: Decimal
    part_partenaire: Decimal
    part_plateforme: Decimal


def _round(value: Decimal, quantum: Decimal) -> Decimal:
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def calculer_frais(montant_facture: Decimal, duree_jours: int, grille) -> ResultatCalculFrais:
    """Calcule les frais et montants d'une avance selon une grille tarifaire degressive.

    `grille` doit exposer : taux_total_minimum, taux_total_maximum, proportion_cedra,
    proportion_partenaire, plafond_montant (optionnel), duree_minimum_jours,
    duree_maximum_jours, taux_avance, type_partenaire (voir app.models.GrilleTarifaire).

    Leve DureeInsuffisanteError si duree_jours est hors de [duree_minimum_jours,
    duree_maximum_jours]. Leve TaegDepasseError (garde-fou non desactivable) si le TAEG
    annualise resultant depasse le plafond legal du type de partenaire.
    """
    montant_facture = Decimal(montant_facture)

    if duree_jours < grille.duree_minimum_jours or duree_jours > grille.duree_maximum_jours:
        raise DureeInsuffisanteError(
            f"La duree de la facture ({duree_jours} jours) est hors de la fenetre eligible "
            f"de la grille ({grille.duree_minimum_jours}-{grille.duree_maximum_jours} jours)."
        )

    progression = (Decimal(duree_jours) - grille.duree_minimum_jours) / (
        Decimal(grille.duree_maximum_jours) - Decimal(grille.duree_minimum_jours)
    )
    taux_total = Decimal(grille.taux_total_minimum) + (
        Decimal(grille.taux_total_maximum) - Decimal(grille.taux_total_minimum)
    ) * progression

    taux_cedra = taux_total * Decimal(grille.proportion_cedra)
    taux_partenaire = taux_total * Decimal(grille.proportion_partenaire)

    commission_plateforme = montant_facture * taux_cedra
    if grille.plafond_montant is not None:
        commission_plateforme = min(commission_plateforme, Decimal(grille.plafond_montant))
    commission_plateforme = _round(commission_plateforme, TWO_PLACES)

    frais_partenaire = _round(montant_facture * taux_partenaire, TWO_PLACES)
    frais_total = commission_plateforme + frais_partenaire

    taeg_annualise = (frais_total / montant_facture) * (JOURS_ANNEE / Decimal(duree_jours))
    taeg_annualise = _round(taeg_annualise, FOUR_PLACES)

    plafond_legal = PLAFOND_TAEG_IMF if grille.type_partenaire == "imf" else PLAFOND_TAEG_BANQUE
    if taeg_annualise > plafond_legal:
        raise TaegDepasseError(
            f"Le TAEG annualise calcule ({taeg_annualise:.2%}) depasse le plafond legal "
            f"({plafond_legal:.0%}) autorise pour ce type de partenaire. Operation refusee."
        )

    montant_avance_initial = _round(montant_facture * Decimal(grille.taux_avance), TWO_PLACES)
    montant_solde_du = _round(montant_facture - montant_avance_initial - frais_total, TWO_PLACES)

    return ResultatCalculFrais(
        montant_avance_initial=montant_avance_initial,
        montant_solde_du=montant_solde_du,
        frais_total=frais_total,
        taux_total_applique=_round(taux_total, FOUR_PLACES),
        taeg_annualise=taeg_annualise,
        part_partenaire=frais_partenaire,
        part_plateforme=commission_plateforme,
    )
