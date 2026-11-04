"""Add the explicit ORM index on kullanici.kullanici_id."""
from alembic import op

revision = "0002_add_kullanici_id_index"
down_revision = "0001_initial_baseline"
branch_labels = None
depends_on = None

def upgrade():
    op.create_index("ix_kullanici_kullanici_id", "kullanici", ["kullanici_id"])

def downgrade():
    op.drop_index("ix_kullanici_kullanici_id", table_name="kullanici")
