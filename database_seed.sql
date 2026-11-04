-- Başlangıç verisi: ilçeler ve ürünler.
-- Önce python -m alembic upgrade head ile tabloları oluşturun;
-- bu dosyayı seçili veritabanında yalnızca bir kez çalıştırın. Ardından kota için:
--   python -m app.scripts.insert_kota
--
-- Ürün adları data/processed/data_files altındaki veri setleriyle birebir aynı
-- olmalıdır (ör. BROKOLI, BROKOLİ değil): fiyat ve risk hesapları bu adlarla eşleşir.

INSERT INTO ilce (ilce_adi) VALUES
    ('Bayındır'),
    ('Bergama'),
    ('Menderes'),
    ('Tire'),
    ('Torbalı'),
    ('Ödemiş');

-- "Boş", tarlada henüz ekilmemiş alanı temsil eder; öneriler bu alana yapılır.
INSERT INTO urun (urun_adi, aktif) VALUES
    ('BIBER SIVRI', TRUE),
    ('DOMATES SALKIM', TRUE),
    ('SALATALIK SILOR', TRUE),
    ('KABAK TAZE', TRUE),
    ('KARPUZ', TRUE),
    ('PATLICAN UZUN', TRUE),
    ('Boş', TRUE),
    ('BAKLA', TRUE),
    ('BEZELYE', TRUE),
    ('BROKOLI', TRUE),
    ('ISPANAK', TRUE),
    ('KARNABAHAR', TRUE),
    ('LAHANA BEYAZ', TRUE),
    ('LAHANA KIRMIZI', TRUE),
    ('MARUL', TRUE),
    ('PIRASA', TRUE);
