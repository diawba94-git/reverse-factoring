import uuid

from fastapi import HTTPException, status

from app.models.enums import RoleUtilisateur, TypeEntreprise
from app.models.utilisateur import Utilisateur

# Which Utilisateur roles a given Entreprise type is allowed to create for itself, whether
# via self-registration or via invitation. `admin` never appears here on purpose: it is
# never attributable through either of those paths (see app.routers.auth._ROLES_INTERNES).
ROLES_AUTORISES_PAR_TYPE: dict[TypeEntreprise, set[RoleUtilisateur]] = {
    TypeEntreprise.PME: {RoleUtilisateur.MEMBRE_PME},
    TypeEntreprise.GRANDE_ENTREPRISE: {RoleUtilisateur.VALIDATEUR_1, RoleUtilisateur.VALIDATEUR_2},
    TypeEntreprise.PARTENAIRE_FINANCIER: {RoleUtilisateur.AGENT_FINANCIER},
}

# The role assigned to the single first user created by /auth/register-entreprise, where
# there is no invitation form to ask "which role" (PME and PARTENAIRE_FINANCIER only ever
# have one possible role anyway; GRANDE_ENTREPRISE arbitrarily starts as validateur_1 — the
# first user can then invite a colleague as validateur_2, or more validateur_1s/2s).
ROLE_PAR_DEFAUT_PAR_TYPE: dict[TypeEntreprise, RoleUtilisateur] = {
    TypeEntreprise.PME: RoleUtilisateur.MEMBRE_PME,
    TypeEntreprise.GRANDE_ENTREPRISE: RoleUtilisateur.VALIDATEUR_1,
    TypeEntreprise.PARTENAIRE_FINANCIER: RoleUtilisateur.AGENT_FINANCIER,
}

ROLES_VALIDATEURS = {RoleUtilisateur.VALIDATEUR_1, RoleUtilisateur.VALIDATEUR_2}


def resoudre_pme_id(current_user: Utilisateur, pme_id_demande: uuid.UUID | None) -> uuid.UUID:
    """Determine quelle PME est concernee par l'action, pour les routes que l'interface
    PME expose aussi a l'admin (qui doit d'abord choisir une entreprise). Un membre_pme
    n'agit jamais que sur sa propre entreprise, quelle que soit la valeur qu'il enverrait
    (jamais deduite depuis un pme_id fourni par le client pour ce role). Un admin doit au
    contraire toujours preciser explicitement quelle PME il consulte : jamais de
    deduction implicite de son cote."""
    if current_user.role == RoleUtilisateur.ADMIN:
        if pme_id_demande is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="pme_id est requis pour un administrateur agissant au nom d'une entreprise",
            )
        return pme_id_demande
    return current_user.entreprise_id
