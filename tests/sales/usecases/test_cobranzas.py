"""0006b, T4: pagos de una cobranza y métodos de pago (RF-VEN-54 a 57, 59)."""

import threading
from datetime import date
from decimal import Decimal as D

import pytest
from django.db import connection

from sales.application import cobranzas as uc
from sales.domain.errores import CobranzaInvalida
from sales.infrastructure.contenedor import caso_de_cobranza, metodos_activos, sembrar_metodos_pago
from sales.infrastructure.models import Cobranza, MetodoPago, Pago
from shared.application.autorizacion import Actor
from shared.domain.errores import AccesoDenegado
from shared.domain.tenant import tenant_context
from tests.sales.usecases.test_facturacion import HOY, aprobado, facturar, preparar


def base(empresa, actor):
    v = preparar(empresa, actor)
    sembrar_metodos_pago(empresa.id, actor.usuario_id, HOY)
    pedido = aprobado(v, ("TER-IPA-330", "24", "12"))
    facturar(v, pedido)
    v["cobranza"] = Cobranza.objects.get(pedido_id=pedido).id
    v["metodo"] = {m.nombre: m.id for m in MetodoPago.objects.all()}
    return v


@pytest.fixture
def v(empresa_ventas):
    return base(*empresa_ventas)


def pagar(v, monto, metodo="Efectivo", fecha=HOY, actor=None):
    datos = uc.DatosPago(v["metodo"][metodo], D(monto), fecha, "op-123")
    return caso_de_cobranza(uc.RegistrarPago).ejecutar(
        actor or v["actor"], v["cobranza"], datos, HOY
    )


def cobranza(v):
    c = Cobranza.objects.get(pk=v["cobranza"])
    return c.estado, c.pagado


@pytest.mark.django_db
def test_pago_parcial_y_total(v):
    """RF-VEN-54: Pendiente hasta que los pagos suman el total."""
    pago = pagar(v, "100.00", "Transferencia")
    assert cobranza(v) == ("PENDIENTE", D("100.00"))
    p = Pago.objects.get(pk=pago)
    assert (p.monto, p.referencia, p.registrado_por_id) == (
        D("100.00"), "op-123", v["actor"].usuario_id
    )  # fmt: skip
    pagar(v, "188.00", "Yape")
    assert cobranza(v) == ("PAGADA", D("288.00"))


@pytest.mark.django_db
@pytest.mark.parametrize(
    "previo, monto, mensaje",
    [
        (None, "300.00", r"no superar el saldo \(288.00\)"),
        ("100.00", "0", r"no superar el saldo \(188.00\)"),
        ("288.00", "1.00", "La cobranza ya está pagada"),
    ],
)
def test_pagos_que_no_se_aceptan(v, previo, monto, mensaje):
    """RF-VEN-55 y 57."""
    if previo:
        pagar(v, previo)
    with pytest.raises(CobranzaInvalida, match=mensaje):
        pagar(v, monto)


@pytest.mark.django_db
def test_fecha_futura_y_metodo_inactivo(v):
    """RF-VEN-54 y 59."""
    with pytest.raises(CobranzaInvalida, match="La fecha del pago no puede ser futura"):
        pagar(v, "10.00", fecha=date(2026, 12, 2))
    MetodoPago.objects.filter(nombre="Plin").update(activo=False)
    with pytest.raises(CobranzaInvalida, match="El método de pago no existe o está inactivo"):
        pagar(v, "10.00", "Plin")


@pytest.mark.django_db
def test_anular_pago(v):
    """RF-VEN-56: con motivo, una sola vez; la cobranza vuelve a Pendiente."""
    pago = pagar(v, "288.00")
    anular = caso_de_cobranza(uc.AnularPago)
    with pytest.raises(CobranzaInvalida, match="Indica el motivo"):
        anular.ejecutar(v["actor"], pago, " ")
    anular.ejecutar(v["actor"], pago, "Monto mal digitado")
    assert cobranza(v) == ("PENDIENTE", D("0.00"))
    p = Pago.objects.get(pk=pago)
    assert (p.motivo_anulacion, p.anulado_por_id) == ("Monto mal digitado", v["actor"].usuario_id)
    with pytest.raises(CobranzaInvalida, match="El pago ya está anulado"):
        anular.ejecutar(v["actor"], pago, "Otra vez")
    pagar(v, "288.00")  # el saldo vuelve a estar disponible
    assert cobranza(v) == ("PAGADA", D("288.00"))


@pytest.mark.django_db
def test_metodos_de_pago(v):
    """RF-VEN-59: nombre único sin mayúsculas, renombrar, desactivar; el inactivo no se
    ofrece."""
    guardar = caso_de_cobranza(uc.GuardarMetodoPago)
    with pytest.raises(CobranzaInvalida, match="Ya existe un método de pago con ese nombre"):
        guardar.ejecutar(v["actor"], None, " yape ")
    with pytest.raises(CobranzaInvalida, match="Indica el nombre"):
        guardar.ejecutar(v["actor"], None, " ")
    nuevo = guardar.ejecutar(v["actor"], None, "Depósito BCP")
    guardar.ejecutar(v["actor"], nuevo, "Depósito en cuenta")
    guardar.ejecutar(v["actor"], v["metodo"]["Yape"], "YAPE")  # el mismo, otras mayúsculas
    caso_de_cobranza(uc.CambiarEstadoMetodoPago).ejecutar(v["actor"], v["metodo"]["Plin"], False)
    assert [m.nombre for m in metodos_activos()] == [
        "Depósito en cuenta", "Efectivo", "Tarjeta", "Transferencia", "YAPE"
    ]  # fmt: skip


@pytest.mark.django_db
def test_permisos(v):
    """RF-VEN-54 y 59: `ventas.cobranza.gestionar`."""
    a = v["actor"]
    sin = Actor(a.usuario_id, a.empresa_id, a.permisos - {uc.GESTIONAR})
    with pytest.raises(AccesoDenegado):
        pagar(v, "10.00", actor=sin)
    with pytest.raises(AccesoDenegado):
        caso_de_cobranza(uc.GuardarMetodoPago).ejecutar(sin, None, "Otro")


@pytest.mark.django_db(transaction=True)
def test_dos_pagos_por_el_ultimo_saldo(empresa_ventas):
    """Caso límite: dos pagos simultáneos por el saldo; solo uno entra."""
    empresa, actor = empresa_ventas
    v = base(empresa, actor)
    barrera, resultados = threading.Barrier(2), []

    def pagar_en_hilo():
        try:
            with tenant_context(empresa.id):
                barrera.wait(timeout=5)
                pagar(v, "288.00")
            resultados.append("ok")
        except CobranzaInvalida as e:
            resultados.append(e.mensaje)
        finally:
            connection.close()

    hilos = [threading.Thread(target=pagar_en_hilo) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=15)
    assert sorted(resultados) == ["La cobranza ya está pagada", "ok"]
    assert cobranza(v) == ("PAGADA", D("288.00"))
