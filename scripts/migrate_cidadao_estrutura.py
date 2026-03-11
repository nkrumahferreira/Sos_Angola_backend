"""
Migração: adiciona colunas e tabelas da nova estrutura do cidadão (data_nascimento, bi, cuidados especiais, etc.).
Uso: python -m scripts.migrate_cidadao_estrutura
Requer: .env com DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
Executa ALTER TABLE e CREATE TABLE conforme necessário. Seguro para bases já existentes.
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

def get_engine():
    from app.config import settings
    from sqlalchemy import create_engine
    return create_engine(settings.DATABASE_URL, pool_pre_ping=True)


def column_exists(conn, table: str, column: str) -> bool:
    from sqlalchemy import text
    if conn.dialect.name == "postgresql":
        r = conn.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name = :t AND column_name = :c
        """), {"t": table, "c": column})
        return r.fetchone() is not None
    return False


def table_exists(conn, table: str) -> bool:
    from sqlalchemy import text
    if conn.dialect.name == "postgresql":
        r = conn.execute(text("""
            SELECT 1 FROM information_schema.tables WHERE table_name = :t
        """), {"t": table})
        return r.fetchone() is not None
    return False


def run_migration(engine):
    from sqlalchemy import text

    with engine.connect() as conn:
        # --- cidadao: novas colunas ---
        for col, sql in [
            ("data_nascimento", "ALTER TABLE cidadao ADD COLUMN data_nascimento DATE"),
            ("bi", "ALTER TABLE cidadao ADD COLUMN bi VARCHAR(50) UNIQUE"),
            ("fotografia_url", "ALTER TABLE cidadao ADD COLUMN fotografia_url VARCHAR(500)"),
            ("fotografia_base64", "ALTER TABLE cidadao ADD COLUMN fotografia_base64 TEXT"),
            ("genero", "ALTER TABLE cidadao ADD COLUMN genero VARCHAR(20)"),
            ("precisa_cuidados_especiais", "ALTER TABLE cidadao ADD COLUMN precisa_cuidados_especiais BOOLEAN DEFAULT FALSE"),
        ]:
            if not column_exists(conn, "cidadao", col):
                conn.execute(text(sql))
                conn.commit()
                print(f"  cidadao: coluna '{col}' adicionada.")

        # Se a tabela tinha 'idade' e não tem 'data_nascimento' com dados, podemos manter idade para leitura antiga.
        # Não removemos a coluna idade para não quebrar dados existentes.

        # --- contato_emergencia: tipo ---
        if not column_exists(conn, "contato_emergencia", "tipo"):
            conn.execute(text("ALTER TABLE contato_emergencia ADD COLUMN tipo VARCHAR(30)"))
            conn.commit()
            print("  contato_emergencia: coluna 'tipo' adicionada.")

        # --- alerta: colunas para SOS (autoridade_destino, cancelamento, streaming loc) ---
        for col, sql in [
            ("ultima_latitude", "ALTER TABLE alerta ADD COLUMN ultima_latitude FLOAT"),
            ("ultima_longitude", "ALTER TABLE alerta ADD COLUMN ultima_longitude FLOAT"),
            ("ultima_localizacao_at", "ALTER TABLE alerta ADD COLUMN ultima_localizacao_at TIMESTAMP WITH TIME ZONE"),
            ("autoridade_destino", "ALTER TABLE alerta ADD COLUMN autoridade_destino VARCHAR(30)"),
            ("tipo_ocorrencia", "ALTER TABLE alerta ADD COLUMN tipo_ocorrencia VARCHAR(80)"),
            ("motivo_cancelamento", "ALTER TABLE alerta ADD COLUMN motivo_cancelamento VARCHAR(200)"),
            ("cancelado_at", "ALTER TABLE alerta ADD COLUMN cancelado_at TIMESTAMP WITH TIME ZONE"),
        ]:
            if table_exists(conn, "alerta") and not column_exists(conn, "alerta", col):
                conn.execute(text(sql))
                conn.commit()
                print(f"  alerta: coluna '{col}' adicionada.")

        # --- Novas tabelas (cuidados_especiais, medicacao_cidadao) via create_all ---
        from app.database import Base
        from app.models import models  # noqa: F401
        Base.metadata.create_all(bind=engine, checkfirst=True)
        if not table_exists(conn, "cuidados_especiais"):
            print("  Tabela cuidados_especiais criada.")
        if not table_exists(conn, "medicacao_cidadao"):
            print("  Tabela medicacao_cidadao criada.")

    print("Migração concluída.")


def main():
    try:
        engine = get_engine()
        run_migration(engine)
    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
