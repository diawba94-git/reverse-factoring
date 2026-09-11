from app.models.enums import FormeJuridique

_FORMES_JURIDIQUES_SANS_RCCM = {FormeJuridique.PERSONNE_PHYSIQUE_ENTREPRISE_INDIVIDUELLE}


def rccm_est_obligatoire(forme_juridique: FormeJuridique) -> bool:
    return forme_juridique not in _FORMES_JURIDIQUES_SANS_RCCM
