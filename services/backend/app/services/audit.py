import uuid

from sqlalchemy.orm import Session

from app.models.journal_audit import JournalAudit


def _to_jsonable(value):
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def enregistrer_audit(
    db: Session,
    *,
    entite_type: str,
    entite_id: uuid.UUID,
    action: str,
    utilisateur_id: uuid.UUID | None,
    valeur_apres: dict,
    valeur_avant: dict | None = None,
) -> JournalAudit:
    entree = JournalAudit(
        entite_type=entite_type,
        entite_id=entite_id,
        action=action,
        utilisateur_id=utilisateur_id,
        valeur_avant=_to_jsonable(valeur_avant) if valeur_avant is not None else None,
        valeur_apres=_to_jsonable(valeur_apres),
    )
    db.add(entree)
    return entree
