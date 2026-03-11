"""
Endpoints internos para jobs em background (ex.: verificação de medicação ignorada).
Protegidos por chave (CRON_SECRET).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header

from app.config import settings
from app.database import get_db
from app.schemas.alerta import AlertaResponse
from app.services.cidadao_service import verificar_e_registar_doses_ignoradas
from app.utils.ws_manager import ws_manager

router = APIRouter(prefix="/internal", tags=["Internal"])


def _check_cron_secret(x_cron_secret: str | None = Header(None, alias="X-Cron-Secret")):
    if not settings.CRON_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRON_SECRET não configurado.",
        )
    if x_cron_secret != settings.CRON_SECRET:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chave inválida.")


@router.get("/verificar-medicacao-ignorada")
async def verificar_medicacao_ignorada(
    db=Depends(get_db),
    _=Depends(_check_cron_secret),
):
    """
    Job: encontra medicações com proxima_dose no passado, regista como ignorada.
    Se 3 seguidas, cria alerta às autoridades. Emite os alertas por WebSocket.
    """
    alertas = verificar_e_registar_doses_ignoradas(db)
    for alerta in alertas:
        payload = {"evento": "novo_alerta", "alerta": AlertaResponse.model_validate(alerta).model_dump(mode="json")}
        await ws_manager.broadcast_alertas(payload)
    return {"processados": True, "alertas_criados": len(alertas)}
