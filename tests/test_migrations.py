from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

def test_initial_migration_creates_current_model_schema(tmp_path, monkeypatch):
    db_path = tmp_path / "fresh.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    command.upgrade(Config(str(Path(__file__).parents[1] / "alembic.ini")), "head")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    tables = set(inspect(engine).get_table_names())
    expected = {"alembic_version", "kullanici", "ilce", "urun", "tarla", "tarla_urun", "kota", "oneri_paketi", "ekim_kaydi", "risk_analiz_log", "kullanici_aktivite_log"}
    assert expected <= tables
    columns = {c["name"] for c in inspect(engine).get_columns("risk_analiz_log")}
    assert {"ilce_id", "genel_risk", "risk_seviyesi"} <= columns
    assert any(index["name"] == "ix_kullanici_kullanici_id" for index in inspect(engine).get_indexes("kullanici"))
    with engine.connect() as conn:
        assert conn.execute(text("select version_num from alembic_version")).scalar_one() == "0002_add_kullanici_id_index"

def test_migration_config_accepts_percent_encoded_password(tmp_path, monkeypatch):
    db_path = tmp_path / "offline.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}?password=100%25")
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(config, "head", sql=True)
