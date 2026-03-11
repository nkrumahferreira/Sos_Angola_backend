"""
SOS Angola Backend - FastAPI
API para app mobile (cidadãos) e dashboard (autoridades).
"""
import threading
import time
import urllib.request
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

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
    internal_router,
)

app = FastAPI(
    title=settings.APP_NAME,
    description="API para o sistema SOS Angola: alertas, autoridades, chat e notícias.",
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    servers=[{"url": "http://127.0.0.1:8000", "description": "Local (use no browser)"}],
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
app.include_router(internal_router, prefix="/api/v1")

# Ficheiros de upload (relatórios vídeo, etc.)
app.mount("/api/v1/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


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

    # Job em background: a cada 15 min verifica medicações com dose em atraso e regista como ignorada
    def _job_medicacao_ignorada():
        if not settings.CRON_SECRET:
            return
        url = f"http://127.0.0.1:{settings.PORT}/api/v1/internal/verificar-medicacao-ignorada"
        req = urllib.request.Request(url, headers={"X-Cron-Secret": settings.CRON_SECRET})
        time.sleep(60)  # primeira execução 1 min após o arranque
        while True:
            try:
                urllib.request.urlopen(req, timeout=30)
            except Exception:
                pass
            time.sleep(900)  # 15 minutos

    if settings.CRON_SECRET:
        t = threading.Thread(target=_job_medicacao_ignorada, daemon=True)
        t.start()
        print("Job de medicação ignorada (cada 15 min) iniciado.")


@app.get("/")
def root():
    return {
        "message": "SOS Angola API está a funcionar.",
        "docs": "http://127.0.0.1:8000/docs",
        "redoc": "http://127.0.0.1:8000/redoc",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
