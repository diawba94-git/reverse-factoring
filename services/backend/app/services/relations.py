import uuid

from sqlalchemy.orm import Session

from app.models.convention_domiciliation import CompteDedie, ConventionDomiciliation
from app.models.relation_pme_donneur_ordre import RelationPmeDonneurOrdre, ValidateurRelation
from app.models.utilisateur import Utilisateur


def obtenir_ou_creer_relation(db: Session, *, pme_id: uuid.UUID, donneur_ordre_id: uuid.UUID) -> RelationPmeDonneurOrdre:
    relation = (
        db.query(RelationPmeDonneurOrdre)
        .filter(RelationPmeDonneurOrdre.pme_id == pme_id, RelationPmeDonneurOrdre.donneur_ordre_id == donneur_ordre_id)
        .first()
    )
    if relation is None:
        relation = RelationPmeDonneurOrdre(pme_id=pme_id, donneur_ordre_id=donneur_ordre_id)
        db.add(relation)
        db.flush()
        compte = CompteDedie(
            relation_id=relation.id,
            numero_compte=f"CD-{uuid.uuid4().hex[:10].upper()}",
            banque_teneur="Banque Atlantique Sénégal",
        )
        db.add(compte)
        db.flush()
        db.add(ConventionDomiciliation(relation_id=relation.id, compte_dedie_id=compte.id))
    return relation


def affecter_validateur(db: Session, *, relation_id: uuid.UUID, utilisateur_id: uuid.UUID) -> None:
    existe = (
        db.query(ValidateurRelation)
        .filter(ValidateurRelation.relation_id == relation_id, ValidateurRelation.utilisateur_id == utilisateur_id)
        .first()
    )
    if existe is None:
        db.add(ValidateurRelation(relation_id=relation_id, utilisateur_id=utilisateur_id))


def copier_affectations(db: Session, *, depuis_utilisateur: Utilisateur, vers_utilisateur_id: uuid.UUID) -> None:
    """Doc §5.4 : un second validateur invite par un collegue deja affecte herite des memes
    relations PME<->donneur d'ordre — l'acheteur choisit ensuite librement d'en affecter
    d'autres, ce n'est jamais une contrainte d'unicite en base."""
    relations = (
        db.query(ValidateurRelation.relation_id).filter(ValidateurRelation.utilisateur_id == depuis_utilisateur.id).all()
    )
    for (relation_id,) in relations:
        affecter_validateur(db, relation_id=relation_id, utilisateur_id=vers_utilisateur_id)
