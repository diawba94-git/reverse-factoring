"""email unique pour connexion par email ou telephone

Revision ID: f3e52885a9d0
Revises: bcfdd271d909
Create Date: 2026-09-11 18:36:30.630734

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3e52885a9d0'
down_revision: Union[str, None] = 'bcfdd271d909'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Index fonctionnel sur lower(email) plutot qu'un unique classique : la connexion
    # (voir app.routers.auth.login) compare l'email insensible a la casse, donc
    # l'unicite doit l'etre aussi pour ne pas laisser deux comptes "Foo@x.com" /
    # "foo@x.com" coexister et rendre la recherche de connexion ambigue.
    op.execute(
        "CREATE UNIQUE INDEX ix_utilisateurs_email_lower ON utilisateurs (lower(email))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX ix_utilisateurs_email_lower")
