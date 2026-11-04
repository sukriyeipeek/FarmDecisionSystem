# Veritabanı kurulumu

Yeni veritabanında `DATABASE_URL` ayarlandıktan sonra `python -m alembic upgrade head` çalıştırın. Uygulama başlangıçta tablo oluşturmaz veya güncellemez.

Legacy şemalarda otomatik `stamp` kullanılmaz. Önce yedek alın, mevcut şemayı `database_schema.sql` ve `app/models.py` ile karşılaştırın; eksikleri kontrollü migration ile taşıyın. Yalnızca şemanın baseline ile birebir aynı olduğu doğrulanırsa açık operasyon kararıyla `python -m alembic stamp 0001_initial_baseline` uygulanabilir.

`DATABASE_URL` zorunludur; eski `sifre`/root fallback'i desteklenmez. CI da migration'ı yeni bir veritabanında çalıştırmalıdır.
