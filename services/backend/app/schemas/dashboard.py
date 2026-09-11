from decimal import Decimal

from pydantic import BaseModel


class DashboardPmeOut(BaseModel):
    nombre_factures: int
    montant_total_factures: Decimal
    factures_par_statut: dict[str, int]
    nombre_avances_actives: int
    montant_total_avance_percu: Decimal
    montant_total_solde_du: Decimal


class DashboardDonneurOrdreOut(BaseModel):
    nombre_factures: int
    montant_total_factures: Decimal
    factures_par_statut: dict[str, int]
    score_actuel: Decimal | None


class DashboardPartenaireOut(BaseModel):
    nombre_avances: int
    avances_par_statut: dict[str, int]
    montant_total_avance: Decimal
    montant_total_rembourse: Decimal
    montant_en_defaut: Decimal
    encours: Decimal


class DashboardAdminOut(BaseModel):
    nombre_entreprises: int
    entreprises_par_type: dict[str, int]
    entreprises_creees_ce_mois: dict[str, int]
    # 8 points hebdomadaires (le plus recent en dernier), pour les sparklines des KPI —
    # calcules a partir des created_at reels, jamais de donnees d'exemple.
    evolution_entreprises_hebdo: dict[str, list[int]]
    evolution_volume_hebdo: list[Decimal]
    nombre_utilisateurs: int
    nombre_factures: int
    nombre_avances: int
    montant_total_avance_verse: Decimal
    montant_total_avance_verse_delta_pourcentage: Decimal | None
    montant_total_frais_plateforme: Decimal
    # Repartition de qui detient au final le montant total avance (PME/partenaire/Cedra) —
    # remplace un decoupage "PME/Acheteurs/Partenaires" qui n'a pas d'equivalent reel (un
    # acheteur ne recoit jamais de part du volume finance, il ne fait que rembourser).
    repartition_volume: dict[str, Decimal]
    tickets_ouverts: int
