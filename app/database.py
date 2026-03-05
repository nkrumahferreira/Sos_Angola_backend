from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from fastapi import HTTPException
from app.config import settings

_engine = None
_SessionLocal = None
Base = declarative_base()


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.DATABASE_URL,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            echo=settings.DB_ECHO,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
    return _engine


def get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def get_db():
    try:
        db = get_session_local()()
        try:
            yield db
        finally:
            db.close()
    except Exception as e:
        raise RuntimeError(f"Erro ao conectar ao banco de dados: {e}") from e


def init_db():
    from app.models import models  # noqa: F401 - registra modelos

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
