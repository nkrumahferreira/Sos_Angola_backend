from app.controllers.auth_controller import router as auth_router
from app.controllers.alertas_controller import router as alertas_router
from app.controllers.autoridades_controller import router as autoridades_router
from app.controllers.cidadao_controller import router as cidadao_router
from app.controllers.noticias_controller import router as noticias_router
from app.controllers.localizacao_controller import router as localizacao_router
from app.controllers.chat_controller import router as chat_router
from app.controllers.ws_controller import ws_router
from app.controllers.internal_controller import router as internal_router

__all__ = [
    "auth_router",
    "alertas_router",
    "autoridades_router",
    "cidadao_router",
    "noticias_router",
    "localizacao_router",
    "chat_router",
    "ws_router",
    "internal_router",
]
