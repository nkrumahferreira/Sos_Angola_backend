"""Lista tabelas na base. Uso: python -m scripts.list_tables"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pathlib import Path
(Path(__file__).resolve().parent.parent / ".env").exists() and __import__("dotenv").load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from app.config import settings
from sqlalchemy import create_engine, text
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    r = c.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name"))
    tables = [row[0] for row in r]
print("Tabelas na base sos_angola:", len(tables))
for t in tables:
    print(" -", t)
