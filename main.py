"""
SOS Angola Backend - FastAPI
API para app mobile (cidadãos) e dashboard (autoridades).
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.database import init_db
from app.middleware.exception_handlers import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from app.controllers import (
    auth_router,
    alertas_router,
    autoridades_router,
    cidadao_router,
    noticias_router,
    localizacao_router,
    chat_router,
    ws_router,
)

app = FastAPI(
    title=settings.APP_NAME,
    description="API para o sistema SOS Angola: alertas, autoridades, chat e notícias.",
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(alertas_router, prefix="/api/v1")
app.include_router(autoridades_router, prefix="/api/v1")
app.include_router(cidadao_router, prefix="/api/v1")
app.include_router(noticias_router, prefix="/api/v1")
app.include_router(localizacao_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")


@app.on_event("startup")
def startup_event():
    try:
        settings.get_upload_path()
        if settings.LOG_FILE:
            settings.get_log_path()
    except Exception as e:
        print(f"Aviso ao criar diretórios: {e}")
    try:
        init_db()
        print(f"{settings.APP_NAME} iniciado.")
        print(f"Base de dados: {settings.DB_NAME} em {settings.DB_HOST}:{settings.DB_PORT}")
    except Exception as e:
        print(f"Aviso: não foi possível conectar ao banco: {e}")


@app.get("/")
def root():
    return {"message": "SOS Angola API está a funcionar."}


@app.get("/health")
def health():
    return {"status": "healthy"}
