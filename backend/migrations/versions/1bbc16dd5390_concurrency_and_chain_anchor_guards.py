"""concurrency and chain-anchor guards

Revision ID: 1bbc16dd5390
Revises: 155345136fa9
Create Date: 2026-09-03 16:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1bbc16dd5390"
down_revision: Union[str, Sequence[str], None] = "155345136fa9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("recovery_cases", sa.Column("last_audit_sequence", sa.Integer(), nullable=True))
    op.add_column("recovery_cases", sa.Column("last_audit_hash", sa.String(), nullable=True))
    op.create_unique_constraint(
        "uq_audit_seals_case_sequence", "audit_seals", ["case_id", "sequence"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_audit_seals_case_sequence", "audit_seals", type_="unique")
    op.drop_column("recovery_cases", "last_audit_hash")
    op.drop_column("recovery_cases", "last_audit_sequence")
