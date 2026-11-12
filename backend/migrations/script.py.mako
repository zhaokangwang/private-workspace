"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
"""

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | None = ${repr(branch_labels)}
depends_on: str | None = ${repr(depends_on)}


def upgrade() -> None:
    """应用本次结构变更。"""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """撤销本次结构变更，执行前确认数据已有备份。"""
    ${downgrades if downgrades else "pass"}
