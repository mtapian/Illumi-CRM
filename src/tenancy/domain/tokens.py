"""Tokens de API (spec 0001d; RF-TEN-45 a 47, 54; RNF-TEN-02).

El token se muestra en claro una sola vez, al crearlo (constitución art. 6.2); se guarda
solo su hash SHA-256 y, para reconocerlo, su prefijo.
"""

import hashlib
import secrets
from datetime import date

from tenancy.domain.suscripcion import Estado, puede_operar

API = "transversal.api"
NO_AUTENTICADO = "NO_AUTENTICADO"  # 401
SIN_API = "SIN_API"  # 403


def nuevo_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def prefijo_token(token: str) -> str:
    return token[:8]


def rechazo_token(
    revocado: bool,
    usuario_activo: bool,
    estado: Estado,
    fecha_termino: date | None,
    habilitadas,
    hoy: date,
) -> str | None:
    """None si el token se puede usar; si no, el motivo (RF-TEN-46, 47, 54)."""
    if revocado or not usuario_activo or not puede_operar(estado, fecha_termino, hoy):
        return NO_AUTENTICADO
    if API not in habilitadas:
        return SIN_API
    return None
