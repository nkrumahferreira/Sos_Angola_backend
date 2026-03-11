"""
Migração: adiciona coluna sessao_anonima na tabela alerta (identificador dispositivo/sessão para anónimos).
Uso: python -m scripts.migrate_alerta_sessao_anonima
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
_project_root = Path(__file__).resolve().parent.parent
env_path = _project_root / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)


def column_exists(conn, table: str, column: str) -> bool:
    from sqlalchemy import text
    if conn.dialect.name == "postgresql":
        r = conn.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name = :t AND column_name = :c
        """), {"t": table, "c": column})
        return r.fetchone() is not None
    if conn.dialect.name == "sqlite":
        r = conn.execute(text("PRAGMA table_info(" + table + ")"))
        return any(row[1] == column for row in r.fetchall())
    return False


def main():
    from app.database import get_engine
    from sqlalchemy import text

    engine = get_engine()
    with engine.connect() as conn:
        if column_exists(conn, "alerta", "sessao_anonima"):
            print("Coluna alerta.sessao_anonima já existe. Nada a fazer.")
            return
        conn.execute(text("ALTER TABLE alerta ADD COLUMN sessao_anonima VARCHAR(120)"))
        conn.commit()
    print("Coluna alerta.sessao_anonima adicionada com sucesso.")


if __name__ == "__main__":
    main()
