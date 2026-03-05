"""
Cria o banco de dados PostgreSQL (se não existir) e todas as tabelas do SOS Angola.
Uso: python -m scripts.create_database
Requer: .env com DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
"""
import os
import sys

# Garantir que o projeto está no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Carregar .env na raiz do projeto antes de importar app.config
from pathlib import Path
_project_root = Path(__file__).resolve().parent.parent
env_path = _project_root / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)
else:
    print("Aviso: ficheiro .env não encontrado. Use valores em .env.example e copie para .env")


def get_db_config():
    """Lê configuração do banco a partir do ambiente (compatível com .env)."""
    return {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": int(os.environ.get("DB_PORT", "5432")),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", ""),
        "database": os.environ.get("DB_NAME", "sos_angola"),
    }


def create_database_if_not_exists(config):
    """Conecta à base 'postgres' e cria a base de dados se não existir."""
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    except ImportError:
        print("Erro: instale psycopg2-binary (pip install psycopg2-binary)")
        sys.exit(1)

    conn = None
    try:
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database="postgres",
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (config["database"],),
        )
        exists = cur.fetchone()
        if exists:
            print(f"Base de dados '{config['database']}' já existe.")
        else:
            cur.execute(f'CREATE DATABASE "{config["database"]}"')
            print(f"Base de dados '{config['database']}' criada com sucesso.")

        cur.close()
    except Exception as e:
        print(f"Erro ao criar/verificar a base de dados: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()


def create_tables():
    """Cria todas as tabelas via SQLAlchemy (init_db)."""
    from app.database import init_db, get_engine, Base
    from app.models import models  # noqa: F401 - registra modelos

    try:
        init_db()
        print("Tabelas criadas/atualizadas com sucesso.")
    except Exception as e:
        print(f"Erro ao criar tabelas: {e}")
        sys.exit(1)


def main():
    config = get_db_config()
    print(f"Host: {config['host']}:{config['port']}, utilizador: {config['user']}, base: {config['database']}")
    create_database_if_not_exists(config)
    create_tables()
    print("Concluído.")


if __name__ == "__main__":
    main()
