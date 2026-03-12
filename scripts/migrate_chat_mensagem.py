"""
Migração: adiciona tipo_mensagem e media_url à tabela chat_mensagem e torna conteudo nullable.

Uso (com o virtualenv do backend ativado e a partir da raiz do backend):
  python -m scripts.migrate_chat_mensagem

Requer: psycopg2 (pip install psycopg2-binary) e variáveis de ambiente/.env do projeto.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import get_engine, init_db


def main():
    init_db()
    engine = get_engine()
    # Cada ALTER numa transação separada para que um falhar não impeça os outros
    # 1) Adicionar coluna tipo_mensagem (default 'text')
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                ALTER TABLE chat_mensagem
                ADD COLUMN IF NOT EXISTS tipo_mensagem VARCHAR(20) NOT NULL DEFAULT 'text'
            """))
        print("Coluna tipo_mensagem: OK (adicionada ou já existia).")
    except Exception as e:
        print(f"Coluna tipo_mensagem: {e}")

    # 2) Adicionar coluna media_url
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                ALTER TABLE chat_mensagem
                ADD COLUMN IF NOT EXISTS media_url VARCHAR(500)
            """))
        print("Coluna media_url: OK (adicionada ou já existia).")
    except Exception as e:
        print(f"Coluna media_url: {e}")

    # 3) Tornar conteudo nullable
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                ALTER TABLE chat_mensagem
                ALTER COLUMN conteudo DROP NOT NULL
            """))
        print("Coluna conteudo: OK (agora nullable).")
    except Exception as e:
        print(f"Coluna conteudo: {e} (pode já ser nullable).")

    print("Migração concluída.")


if __name__ == "__main__":
    main()
