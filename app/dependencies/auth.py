"""
Dependências de autenticação: cidadão (app) e autoridade (dashboard).
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyQuery
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.utils.jwt_utils import decode_access_token

# Token opcional para rotas que aceitam anónimo ou logado (ex: SOS rápido)
security_optional = HTTPBearer(auto_error=False)
# Token obrigatório para rotas protegidas
security = HTTPBearer()


def get_current_user_id_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
) -> Optional[int]:
    """Retorna o user_id do token se existir e for válido; caso contrário None."""
    if not credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None
    sub = payload.get("sub")
    if sub is None:
        return None
    try:
        return int(sub)
    except (ValueError, TypeError):
        return None


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """Exige token válido e retorna o user_id. Para uso em rotas de cidadão logado."""
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return int(sub)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_role(payload: dict) -> Optional[str]:
    """Retorna o role do token: 'cidadao' ou 'autoridade'."""
    return payload.get("role")


def require_autoridade(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Dependência para rotas do dashboard: exige token de autoridade.
    Retorna o payload (sub, role, etc.) para uso no endpoint.
    """
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload.get("role") != "autoridade":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso reservado às autoridades.",
        )
    return payload
