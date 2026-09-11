import uuid
from datetime import datetime

from app.models.enums import RoleValidateur
from app.schemas.common import ORMBase


class ValidationFactureOut(ORMBase):
    id: uuid.UUID
    facture_id: uuid.UUID
    utilisateur_id: uuid.UUID
    role_validateur: RoleValidateur
    date_validation: datetime
    commentaire: str | None
