"""lignes facture, entreprise adresse, creation native

Revision ID: f3737a824497
Revises: 3e8158c52573
Create Date: 2026-08-24 15:58:55.041459

Hand-adjusted : entreprises.adresse est NOT NULL, donc sur une base avec des entreprises
existantes elle doit d'abord etre ajoutee nullable, backfillee avec une valeur
temporaire explicite (a faire completer ensuite par chaque entreprise), puis contrainte -
l'autogenerate direct en NOT NULL echouerait sur toute ligne preexistante. Ajoute aussi le
label CREATION_NATIVE au type source_creation_facture (non detecte par autogenerate, comme
pour REJETEE_CONFORMITE dans la migration precedente).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3737a824497'
down_revision: Union[str, None] = '3e8158c52573'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ADRESSE_TEMPORAIRE = 'Adresse a renseigner'


def upgrade() -> None:
    op.execute("ALTER TYPE source_creation_facture ADD VALUE IF NOT EXISTS 'CREATION_NATIVE'")

    op.create_table('lignes_facture',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('facture_id', sa.UUID(), nullable=False),
    sa.Column('ordre', sa.Integer(), nullable=False),
    sa.Column('designation', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('quantite', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('prix_unitaire', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('montant_ligne', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.ForeignKeyConstraint(['facture_id'], ['factures.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.add_column('entreprises', sa.Column('adresse', sa.String(length=500), nullable=True))
    op.execute(f"UPDATE entreprises SET adresse = '{_ADRESSE_TEMPORAIRE}' WHERE adresse IS NULL")
    op.alter_column('entreprises', 'adresse', nullable=False)


def downgrade() -> None:
    op.drop_column('entreprises', 'adresse')
    op.drop_table('lignes_facture')
    # Note : Postgres ne permet pas de retirer une valeur d'enum ; CREATION_NATIVE reste
    # dans le type source_creation_facture apres ce downgrade (inoffensif, simplement inutilisee).
