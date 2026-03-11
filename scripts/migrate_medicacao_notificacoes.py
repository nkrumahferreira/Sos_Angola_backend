"""
Migração: adiciona colunas em medicacao_cidadao para notificações (tipo_frequencia, intervalo, dias_semana, controle).
Uso: python -m scripts.migrate_medicacao_notificacoes
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


def run(engine):
    from sqlalchemy import text
    with engine.connect() as conn:
        is_pg = conn.dialect.name == "postgresql"
        ts_type = "TIMESTAMP WITH TIME ZONE" if is_pg else "TEXT"
    cols = [
        ("dose_valor", f"ALTER TABLE medicacao_cidadao ADD COLUMN dose_valor FLOAT"),
        ("dose_unidade", "ALTER TABLE medicacao_cidadao ADD COLUMN dose_unidade VARCHAR(30)"),
        ("tipo_frequencia", "ALTER TABLE medicacao_cidadao ADD COLUMN tipo_frequencia VARCHAR(30)"),
        ("intervalo_horas", "ALTER TABLE medicacao_cidadao ADD COLUMN intervalo_horas INTEGER"),
        ("intervalo_dias", "ALTER TABLE medicacao_cidadao ADD COLUMN intervalo_dias INTEGER"),
        ("dias_semana", "ALTER TABLE medicacao_cidadao ADD COLUMN dias_semana TEXT"),
        ("horario_fixo", "ALTER TABLE medicacao_cidadao ADD COLUMN horario_fixo VARCHAR(10)"),
        ("ultima_dose", f"ALTER TABLE medicacao_cidadao ADD COLUMN ultima_dose {ts_type}"),
        ("proxima_dose", f"ALTER TABLE medicacao_cidadao ADD COLUMN proxima_dose {ts_type}"),
        ("estado_atual", "ALTER TABLE medicacao_cidadao ADD COLUMN estado_atual VARCHAR(20)"),
        ("historico_doses", "ALTER TABLE medicacao_cidadao ADD COLUMN historico_doses TEXT"),
    ]
    with engine.connect() as conn:
        for col, sql in cols:
            if not column_exists(conn, "medicacao_cidadao", col):
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"  medicacao_cidadao: coluna '{col}' adicionada.")
                except Exception as e:
                    print(f"  Aviso ao adicionar '{col}': {e}")
        print("Migração medicacao notificações concluída.")


if __name__ == "__main__":
    from app.config import settings
    from sqlalchemy import create_engine
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    run(engine)
