"""0004b, T2 y T3: anular una compra (RF-COM-15, 16, 18, 28, 29)."""

from datetime import date
from decimal import Decimal as D

import pytest
from django.db import transaction
from django.utils import timezone

from inventory.application.servicio import Linea
from inventory.infrastructure.contenedor import inventario
from inventory.infrastructure.models import CostoProducto, Movimiento
from purchasing.application import compras as uc
from purchasing.domain.compra import LineaCompra
from purchasing.domain.errores import CompraInvalida
from purchasing.infrastructure.contenedor import caso_de_compra
from purchasing.infrastructure.models import Compra
from shared.domain.errores import AccesoDenegado
from tenancy.infrastructure.contenedor import actor_de
from tenancy.infrastructure.models import Usuario
from tests.conftest import asignar_rol
from tests.purchasing.usecases.test_compras import base, crear, finalizar  # noqa: F401

pytestmark = pytest.mark.django_db
HOY = timezone.localdate()


def anular(b, compra_id, motivo="Factura errada", actor=None):
    caso_de_compra(uc.AnularCompra).ejecutar(actor or b["actor"], compra_id, motivo)


def costo(producto_id):
    c = CostoProducto.objects.get(producto_id=producto_id)
    return c.cantidad_total, c.valor_total, c.costo_promedio


def test_anular_finalizada_revierte_al_mismo_costo_y_libera_el_documento(base):  # noqa: F811
    """RF-COM-15 y 18: el costo vuelve a lo previo a la compra."""
    previa = crear(base, serie="F001-1", lineas=[LineaCompra(base["malta"], D("100"), D("4"))])
    finalizar(base, previa)
    compra = crear(base)  # 50 KG a 5.00
    finalizar(base, compra)
    assert costo(base["malta"]) == (D("150"), D("650.00"), D("4.333333"))
    anular(base, compra)
    assert costo(base["malta"]) == (D("100"), D("400.00"), D("4.000000"))
    [m] = Movimiento.objects.filter(ref_tipo="COMPRA", ref_id=compra, motivo="ANULACION")
    assert (m.tipo, m.cantidad, m.costo_unitario) == ("SALIDA", D("50"), D("5"))
    c = Compra.objects.get(pk=compra)
    assert (c.estado, c.motivo_anulacion, c.anulada_por_id) == (
        "ANULADA",
        "Factura errada",
        base["actor"].usuario_id,
    )
    assert c.anulada_en is not None
    crear(base)  # el documento se puede registrar de nuevo


@pytest.mark.parametrize("en_proceso", [False, True])
def test_anular_sin_finalizar_solo_cambia_el_estado(base, en_proceso):  # noqa: F811
    """RF-COM-28."""
    compra = crear(base)
    if en_proceso:
        caso_de_compra(uc.PasarAEnProceso).ejecutar(base["actor"], compra)
    anular(base, compra, "Pedido cancelado")
    assert Compra.objects.get(pk=compra).estado == "ANULADA"
    assert not Movimiento.objects.exists()


def test_no_se_anula_si_el_stock_se_consumio(base):  # noqa: F811
    """RF-COM-16: rechazo con el SKU y sin cambios."""
    compra = crear(base)
    finalizar(base, compra)
    with transaction.atomic():
        linea = Linea(base["malta"], base["principal"], D("10"))
        inventario().registrar_salida("MERMA", "AJUSTE", 1, [linea], None, HOY)
    mensaje = (
        "No se puede anular: INS-MALTA tuvo salidas posteriores a la compra. "
        "Corrígela con un ajuste CORRECCION"
    )
    with pytest.raises(CompraInvalida, match=mensaje):
        anular(base, compra)
    assert Compra.objects.get(pk=compra).estado == "FINALIZADA"
    assert not Movimiento.objects.filter(motivo="ANULACION").exists()


def test_motivo_obligatorio_y_anulacion_definitiva(base):  # noqa: F811
    """RF-COM-29: sin motivo no; anulada no se anula, no se edita ni avanza."""
    compra = crear(base)
    with pytest.raises(CompraInvalida, match="El motivo es obligatorio"):
        anular(base, compra, "  ")
    anular(base, compra, "Duplicada")
    with pytest.raises(CompraInvalida, match="La compra ya está anulada"):
        anular(base, compra, "Otra vez")
    with pytest.raises(CompraInvalida, match="La compra está anulada"):
        caso_de_compra(uc.PasarAEnProceso).ejecutar(base["actor"], compra)


def test_sin_permiso_de_anular(base, empresa_compras):  # noqa: F811
    empresa, _ = empresa_compras
    rosa = asignar_rol(
        Usuario.objects.create_user("rosa@andina.pe", "x", empresa=empresa), "Almacén"
    )
    with pytest.raises(AccesoDenegado):
        anular(base, crear(base), actor=actor_de(rosa, date.today()))
