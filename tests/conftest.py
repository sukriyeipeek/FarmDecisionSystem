import os
import tempfile
from pathlib import Path

# app.database ve app.auth import edilmeden once ortam hazirlanmali.
_db_dosyasi = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_dosyasi.as_posix()}"
os.environ["JWT_SECRET"] = "test-anahtari-en-az-32-karakter-uzunlugunda"
