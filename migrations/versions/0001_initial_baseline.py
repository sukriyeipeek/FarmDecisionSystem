"""Initial schema baseline matching app.models."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial_baseline"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("kullanici", sa.Column("kullanici_id", sa.Integer(), primary_key=True), sa.Column("ad_soyad", sa.String(100), nullable=False), sa.Column("email", sa.String(100), nullable=False, unique=True), sa.Column("sifre_hash", sa.String(255), nullable=False), sa.Column("yas", sa.Integer()), sa.Column("cinsiyet", sa.String(20)), sa.Column("telefon", sa.String(20)), sa.Column("kayit_tarihi", sa.DateTime(), server_default=sa.func.now()), sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table("ilce", sa.Column("ilce_id", sa.Integer(), primary_key=True), sa.Column("ilce_adi", sa.String(50), nullable=False, unique=True))
    op.create_table("urun", sa.Column("urun_id", sa.Integer(), primary_key=True), sa.Column("urun_adi", sa.String(50), nullable=False), sa.Column("aktif", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table("tarla", sa.Column("tarla_id", sa.Integer(), primary_key=True), sa.Column("kullanici_id", sa.Integer(), sa.ForeignKey("kullanici.kullanici_id", ondelete="CASCADE"), nullable=False), sa.Column("tarla_adi", sa.String(100)), sa.Column("ilce_id", sa.Integer(), sa.ForeignKey("ilce.ilce_id"), nullable=False))
    op.create_table("tarla_urun", sa.Column("tarla_urun_id", sa.Integer(), primary_key=True), sa.Column("tarla_id", sa.Integer(), sa.ForeignKey("tarla.tarla_id", ondelete="CASCADE")), sa.Column("urun_id", sa.Integer(), sa.ForeignKey("urun.urun_id", ondelete="CASCADE")), sa.Column("donum", sa.Float(), nullable=False))
    op.create_table("kota", sa.Column("kota_id", sa.Integer(), primary_key=True), sa.Column("urun_id", sa.Integer(), sa.ForeignKey("urun.urun_id", ondelete="CASCADE"), nullable=False), sa.Column("ilce_id", sa.Integer(), sa.ForeignKey("ilce.ilce_id"), nullable=False), sa.Column("maksimum_kota", sa.Float(), nullable=False), sa.Column("kullanilan_kota", sa.Float(), server_default="0"))
    op.create_table("oneri_paketi", sa.Column("paket_id", sa.Integer(), primary_key=True), sa.Column("kullanici_id", sa.Integer(), sa.ForeignKey("kullanici.kullanici_id", ondelete="CASCADE"), nullable=False), sa.Column("tarla_id", sa.Integer(), sa.ForeignKey("tarla.tarla_id", ondelete="CASCADE"), nullable=False), sa.Column("hesaplanan_toplam_kar", sa.Float()), sa.Column("basit_skor", sa.Integer()), sa.Column("kabul_edildi_mi", sa.Boolean(), server_default=sa.false()), sa.Column("olusturma_tarihi", sa.DateTime(), server_default=sa.func.now()))
    op.create_table("ekim_kaydi", sa.Column("kayit_id", sa.Integer(), primary_key=True), sa.Column("paket_id", sa.Integer(), sa.ForeignKey("oneri_paketi.paket_id", ondelete="CASCADE"), nullable=False), sa.Column("urun_id", sa.Integer(), sa.ForeignKey("urun.urun_id", ondelete="CASCADE"), nullable=False), sa.Column("ekilen_donum", sa.Float(), nullable=False), sa.Column("durum", sa.Enum("aktif", "hasat_edildi", "iptal", name="durumenum"), nullable=False, server_default="aktif"))
    op.create_table("risk_analiz_log", sa.Column("log_id", sa.Integer(), primary_key=True), sa.Column("kullanici_id", sa.Integer(), sa.ForeignKey("kullanici.kullanici_id", ondelete="SET NULL")), sa.Column("ilce_id", sa.Integer(), sa.ForeignKey("ilce.ilce_id", ondelete="CASCADE"), nullable=False), sa.Column("urun_id", sa.Integer(), sa.ForeignKey("urun.urun_id", ondelete="CASCADE"), nullable=False), sa.Column("sezon", sa.String(20), nullable=False), sa.Column("girilen_donum", sa.Float(), nullable=False), sa.Column("kota_doluluk", sa.Float()), sa.Column("cv_fiyat", sa.Float()), sa.Column("mazot_tahmini", sa.Float()), sa.Column("mazot_riski", sa.Float()), sa.Column("enflasyon_tahmini", sa.Float()), sa.Column("enflasyon_riski", sa.Float()), sa.Column("gubre_guncel", sa.Float()), sa.Column("gubre_riski", sa.Float()), sa.Column("genel_risk", sa.Float()), sa.Column("risk_seviyesi", sa.String(20)), sa.Column("sorgu_tarihi", sa.DateTime(), server_default=sa.func.now()))
    op.create_table("kullanici_aktivite_log", sa.Column("aktivite_id", sa.Integer(), primary_key=True), sa.Column("kullanici_id", sa.Integer(), sa.ForeignKey("kullanici.kullanici_id", ondelete="CASCADE"), nullable=False), sa.Column("islem_tipi", sa.String(100), nullable=False), sa.Column("ip_adresi", sa.String(45)), sa.Column("islem_tarihi", sa.DateTime(), server_default=sa.func.now()))

def downgrade():
    for table in ("kullanici_aktivite_log", "risk_analiz_log", "ekim_kaydi", "oneri_paketi", "kota", "tarla_urun", "tarla", "urun", "ilce", "kullanici"):
        op.drop_table(table)
