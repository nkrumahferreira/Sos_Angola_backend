"""
SOS Angola Backend - FastAPI
API para app mobile (cidadãos) e dashboard (autoridades).
"""
import os
import threading
import time
import urllib.request
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

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
    primeiros_socorros_router,
    quarteis_router,
    cadastro_autoridades_router,
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
app.include_router(primeiros_socorros_router, prefix="/api/v1")
app.include_router(quarteis_router, prefix="/api/v1")
app.include_router(cadastro_autoridades_router, prefix="/api/v1")
app.include_router(localizacao_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")
app.include_router(internal_router, prefix="/api/v1")

# Diretório de uploads (usado por stream-video e por StaticFiles)
_upload_dir = settings.get_upload_path()


@app.get("/api/v1/stream-video/{path:path}")
def stream_video(request: Request, path: str):
    """
    Serve vídeos com Content-Type e Accept-Ranges corretos para o browser reproduzir.
    Suporta pedidos Range (necessário para muitos players).
    """
    if not path or ".." in path or path.startswith("/"):
        raise HTTPException(status_code=404, detail="Not found")
    upload_dir = _upload_dir.resolve()
    file_path = (upload_dir / path).resolve()
    try:
        if not file_path.is_file():
            raise HTTPException(status_code=404, detail="Not found")
        if os.path.commonpath([str(upload_dir), str(file_path)]) != str(upload_dir):
            raise HTTPException(status_code=404, detail="Not found")
    except ValueError:
        raise HTTPException(status_code=404, detail="Not found")
    size = file_path.stat().st_size
    content_type = "video/mp4" if file_path.suffix.lower() == ".mp4" else "video/webm"
    cors_headers = {
        "Accept-Ranges": "bytes",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Expose-Headers": "Content-Length, Content-Range, Accept-Ranges",
    }
    range_header = request.headers.get("range")
    if range_header and range_header.startswith("bytes="):
        try:
            parts = range_header.replace("bytes=", "").split("-")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if len(parts) > 1 and parts[1] else size - 1
            end = min(end, size - 1)
            if start > end or start < 0:
                raise ValueError("invalid range")
            with open(file_path, "rb") as f:
                f.seek(start)
                data = f.read(end - start + 1)
            return Response(
                content=data,
                status_code=206,
                media_type=content_type,
                headers={
                    **cors_headers,
                    "Content-Range": f"bytes {start}-{end}/{size}",
                    "Content-Length": str(len(data)),
                },
            )
        except (ValueError, OSError):
            pass
    return FileResponse(
        file_path,
        media_type=content_type,
        headers=cors_headers,
    )


# Ficheiros de upload: só montar se o diretório existir (evita travar se criar falhar)
if _upload_dir.exists():
    app.mount("/api/v1/uploads", StaticFiles(directory=str(_upload_dir)), name="uploads")


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
        "openapi_json": "http://127.0.0.1:8000/openapi.json",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/ping")
def ping():
    """Resposta mínima para testar se o servidor responde (use 127.0.0.1:8000/ping)."""
    return {"pong": True}
