"""T5: cuándo un token de API se puede usar (RF-TEN-45 a 47, 54)."""

from datetime import date, timedelta

import pytest

from tenancy.domain.auditoria import diferencias
from tenancy.domain.suscripcion import Estado
from tenancy.domain.tokens import (
    NO_AUTENTICADO,
    SIN_API,
    hash_token,
    nuevo_token,
    prefijo_token,
    rechazo_token,
)

HOY = date(2026, 10, 10)
CON_API = {"transversal.api"}
OK = dict(
    revocado=False,
    usuario_activo=True,
    estado=Estado.ACTIVA,
    fecha_termino=HOY,
    habilitadas=CON_API,
    hoy=HOY,
)


@pytest.mark.parametrize(
    "cambio, esperado",
    [
        ({}, None),
        ({"revocado": True}, NO_AUTENTICADO),
        ({"usuario_activo": False}, NO_AUTENTICADO),
        ({"estado": Estado.SUSPENDIDA}, NO_AUTENTICADO),
        ({"fecha_termino": HOY - timedelta(days=1)}, NO_AUTENTICADO),
        ({"habilitadas": set()}, SIN_API),
    ],
)
def test_rechazo_token(cambio, esperado):
    assert rechazo_token(**(OK | cambio)) == esperado


def test_el_token_se_guarda_como_hash_y_se_muestra_su_prefijo():
    token = nuevo_token()
    assert len(token) >= 40 and prefijo_token(token) == token[:8]
    assert hash_token(token) != token and len(hash_token(token)) == 64


def test_diferencias_para_la_auditoria():
    antes = {"nombre": "Gerente", "permisos": ["ventas.venta.anular", "ventas.venta.ver"]}
    despues = {"nombre": "Gerente", "permisos": ["ventas.venta.ver", "ventas.venta.registrar"]}
    assert diferencias(antes, despues) == [
        "ventas.venta.anular: incluido → quitado",
        "ventas.venta.registrar: no incluido → incluido",
    ]
    assert diferencias({"activo": True}, {"activo": False}) == ["activo: sí → no"]
    assert diferencias(None, {"roles": ["Ventas"]}) == ["roles: — → Ventas"]
