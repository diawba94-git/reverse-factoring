import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMBase

PORTEES_VALIDES = {"toutes", "pme", "donneur_ordre", "partenaire_financier"}


def _valider_portee(value: str) -> str:
    if value not in PORTEES_VALIDES:
        raise ValueError(f"Portee invalide (attendu : {', '.join(sorted(PORTEES_VALIDES))})")
    return value


class ArticleFaqCreate(BaseModel):
    question: str = Field(min_length=5, max_length=500)
    reponse: str = Field(min_length=5)
    portee: str = "toutes"
    publie: bool = True

    @field_validator("portee")
    @classmethod
    def _check_portee(cls, value: str) -> str:
        return _valider_portee(value)


class ArticleFaqUpdate(BaseModel):
    question: str | None = Field(default=None, min_length=5, max_length=500)
    reponse: str | None = Field(default=None, min_length=5)
    portee: str | None = None
    publie: bool | None = None

    @field_validator("portee")
    @classmethod
    def _check_portee(cls, value: str | None) -> str | None:
        return _valider_portee(value) if value is not None else None


class ArticleFaqOut(ORMBase):
    id: uuid.UUID
    question: str
    reponse: str
    portee: str
    publie: bool
    created_at: datetime
    updated_at: datetime
