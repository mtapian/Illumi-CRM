"""0006b, T3: facturar y entregar un pedido (RF-VEN-17, 19 a 28, 38, 51)."""

import threading
from datetime import date
from decimal import Decimal as D

import pytest
from django.db import connection, transaction

from catalog.infrastructure.contenedor import sembrar_impuestos
from catalog.infrastructure.models import Impuesto, Producto, ProductoImpuesto, Unidad
from inventory.application.servicio import Linea
from inventory.infrastructure.contenedor import inventario
from inventory.infrastructure.models import Almacen, Movimiento
from sales.application import facturacion as uf
from sales.application import pedidos as up
from sales.domain.cobranza import numero_cobranza
from sales.domain.errores import PedidoInvalido
from sales.domain.facturacion import CONTADO, CREDITO, Cuota
from sales.domain.pedido import LineaPedido
from sales.infrastructure.contenedor import caso_de_factura, caso_de_pedido
from sales.infrastructure.models import Cliente, Cobranza, Pedido
from shared.application.autorizacion import Actor
from shared.domain.errores import AccesoDenegado
from shared.domain.tenant import tenant_context

HOY = date(2026, 12, 1)


def preparar(empresa, actor, hoy=HOY):
    """IGV 18% de venta en los productos; TER-IPA-330 a costo 1.893080 en dos lotes."""
    sembrar_impuestos(empresa.id, actor.usuario_id, hoy)
    igv = Impuesto.objects.get(tipo="VENTA", codigo="IGV")
    und = Unidad.objects.get(abreviatura="UND")
    Producto.objects.create(
        sku="SRV-FLETE", nombre="Flete", unidad=und, tipo="SERVICIO", se_compra=False,
        se_vende=True, se_fabrica=False, precio_venta=D("20"),
    )  # fmt: skip
    ids = {p.sku: p.id for p in Producto.objects.all()}
    for id_ in ids.values():
        ProductoImpuesto.objects.create(producto_id=id_, impuesto=igv)
    almacen = Almacen.objects.get(nombre="Principal").id
    lineas = [
        Linea(ids["TER-IPA-330"], almacen, D(q), D("1.893080"), lote, vence)
        for lote, vence, q in (
            ("IPA-0015", date(2026, 12, 15), "10"),
            ("IPA-0020", date(2027, 3, 25), "1000"),
        )
    ]
    with transaction.atomic():
        inventario().registrar_entrada("COMPRA", "COMPRA", 1, lineas, actor.usuario_id, hoy)
    bar = Cliente.objects.create(nombre="Bar El Lúpulo", tipo_doc="RUC", num_doc="20512345671")
    ana = Cliente.objects.create(nombre="Ana Torres", tipo_doc="DNI", num_doc="45678912")
    varios = Cliente.objects.get(es_generico=True)
    return {
        "actor": actor,
        "ids": ids,
        "almacen": almacen,
        "clientes": {"bar": bar.id, "ana": ana.id, "varios": varios.id},
    }


@pytest.fixture
def v(empresa_ventas):
    empresa, actor = empresa_ventas
    return preparar(empresa, actor)


def aprobado(v, *lineas, cliente="bar"):
    filas = tuple(LineaPedido(v["ids"][sku], D(q), D(precio)) for sku, q, precio in lineas)
    datos = up.DatosPedido(v["clientes"][cliente], date(2026, 12, 5), "", filas)
    id_ = caso_de_pedido(up.CrearPedido).ejecutar(v["actor"], datos)
    caso_de_pedido(up.AprobarPedido).ejecutar(v["actor"], id_, HOY)
    return id_


def facturar(v, pedido_id, forma=CONTADO, cuotas=(), lotes=None, actor=None):
    datos = uf.DatosFactura(v["almacen"], forma, tuple(cuotas), lotes or {})
    caso_de_factura(uf.FacturarPedido).ejecutar(actor or v["actor"], pedido_id, datos, HOY)


def salidas(pedido_id):
    return sorted(
        (m.lote.codigo if m.lote else None, m.cantidad)
        for m in Movimiento.objects.filter(ref_tipo="VENTA", ref_id=pedido_id)
    )


@pytest.mark.django_db
def test_facturar_al_contado(v):
    """RF-VEN-17, 19 a 22, 38: FEFO, costo congelado, desglose, comprobante y cobranza."""
    id_ = aprobado(v, ("TER-IPA-330", "24", "12"))
    facturar(v, id_)
    p = Pedido.objects.get(pk=id_)
    assert (p.estado, p.comprobante, p.forma_pago, p.fecha_emision) == (
        "FACTURADO", "FACTURA", "CONTADO", HOY
    )  # fmt: skip
    assert (p.almacen_id, p.costo_total, p.facturado_por_id) == (
        v["almacen"], D("45.43"), v["actor"].usuario_id
    )  # fmt: skip
    x = p.lineas.get()
    assert (x.valor, x.isc, x.igv, x.costo) == (D("244.07"), D("0.00"), D("43.93"), D("45.43"))
    assert salidas(id_) == [("IPA-0015", D("10")), ("IPA-0020", D("14"))]
    c = Cobranza.objects.get(pedido_id=id_)
    assert (c.estado, c.total, c.pagado, c.emision) == ("PENDIENTE", D("288.00"), D("0"), HOY)
    assert [(q.numero, q.monto, q.vencimiento) for q in c.cuotas.all()] == [(1, D("288.00"), HOY)]
    assert numero_cobranza(c.numero) == "COB-000001"  # código correlativo (PO)
    otro = aprobado(v, ("TER-IPA-330", "1", "12"))
    facturar(v, otro)
    assert Cobranza.objects.get(pedido_id=otro).numero == 2


@pytest.mark.django_db
def test_lote_elegido_y_servicio(v):
    """RF-VEN-20: el lote elegido; un servicio no saca stock."""
    id_ = aprobado(v, ("TER-IPA-330", "24", "12"), ("SRV-FLETE", "1", "20"))
    facturar(v, id_, lotes={v["ids"]["TER-IPA-330"]: "IPA-0020"})
    assert salidas(id_) == [("IPA-0020", D("24"))]
    flete = Pedido.objects.get(pk=id_).lineas.get(producto_id=v["ids"]["SRV-FLETE"])
    assert (flete.valor, flete.igv, flete.costo) == (D("16.95"), D("3.05"), D("0"))


@pytest.mark.django_db
def test_doble_validacion_del_stock_y_nada_cambia(v):
    """RF-VEN-17 y 26: facturar vuelve a validar el stock; si falla, no mueve nada."""
    id_ = aprobado(v, ("TER-IPA-330", "1000", "12"))
    otra = Linea(v["ids"]["TER-IPA-330"], v["almacen"], D("20"), lote="IPA-0020")
    with transaction.atomic():
        inventario().registrar_salida("MERMA", "AJUSTE", 1, [otra], v["actor"].usuario_id, HOY)
    with pytest.raises(PedidoInvalido, match="Stock insuficiente: TER-IPA-330 faltan 10"):
        facturar(v, id_)
    p = Pedido.objects.get(pk=id_)
    assert (p.estado, p.comprobante, salidas(id_)) == ("APROBADO", "", [])
    assert not Cobranza.objects.exists()
    with pytest.raises(PedidoInvalido, match=r"TER-IPA-330 \(IPA-0015\) faltan 990"):
        facturar(v, id_, lotes={v["ids"]["TER-IPA-330"]: "IPA-0015"})


@pytest.mark.django_db
def test_producto_desactivado_despues_de_aprobar(v):
    """RF-VEN-23 (doble validación)."""
    id_ = aprobado(v, ("TER-IPA-330", "24", "12"))
    Producto.objects.filter(pk=v["ids"]["TER-IPA-330"]).update(activo=False)
    with pytest.raises(PedidoInvalido, match="TER-IPA-330 ya no se vende"):
        facturar(v, id_)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "cliente, cantidad, resultado",
    [
        ("bar", "60", "FACTURA"),
        ("ana", "60", "BOLETA"),
        ("varios", "24", "BOLETA"),
        ("varios", "60", "Las boletas mayores a S/ 700.00 requieren identificar al cliente"),
    ],
)
def test_el_comprobante_sale_del_cliente(v, cliente, cantidad, resultado):
    """RF-VEN-19, 24 y 25."""
    id_ = aprobado(v, ("TER-IPA-330", cantidad, "12"), cliente=cliente)
    try:
        facturar(v, id_)
    except PedidoInvalido as e:
        assert e.mensaje == resultado
    else:
        assert Pedido.objects.get(pk=id_).comprobante == resultado


@pytest.mark.django_db
def test_credito_en_cuotas(v):
    """RF-VEN-19 y 27: la factura a crédito guarda su cronograma; sin RUC no hay crédito."""
    id_ = aprobado(v, ("TER-IPA-330", "24", "12"))
    cuotas = (Cuota(D("144.00"), date(2026, 12, 31)), Cuota(D("144.00"), date(2026, 12, 16)))
    facturar(v, id_, CREDITO, cuotas)
    p = Pedido.objects.get(pk=id_)
    assert p.forma_pago == "CREDITO"
    assert [(q.numero, q.vencimiento) for q in p.cobranza.cuotas.order_by("numero")] == [
        (1, date(2026, 12, 16)),
        (2, date(2026, 12, 31)),
    ]
    ana = aprobado(v, ("TER-IPA-330", "1", "12"), cliente="ana")
    with pytest.raises(PedidoInvalido, match=r"requiere factura \(cliente con RUC\)"):
        facturar(v, ana, CREDITO, (Cuota(D("12.00"), date(2026, 12, 31)),))


@pytest.mark.django_db
def test_estado_y_permiso(v):
    """RF-VEN-17: solo un Aprobado, con `ventas.venta.registrar`."""
    actor = v["actor"]
    filas = (LineaPedido(v["ids"]["TER-IPA-330"], D("1"), D("12")),)
    creado = caso_de_pedido(up.CrearPedido).ejecutar(
        actor, up.DatosPedido(v["clientes"]["bar"], date(2026, 12, 5), "", filas)
    )
    with pytest.raises(PedidoInvalido, match="El pedido debe estar aprobado para facturarlo"):
        facturar(v, creado)
    sin = Actor(actor.usuario_id, actor.empresa_id, actor.permisos - {uf.REGISTRAR})
    with pytest.raises(AccesoDenegado):
        facturar(v, aprobado(v, ("TER-IPA-330", "1", "12")), actor=sin)


@pytest.mark.django_db
def test_entregar(v):
    """RF-VEN-51: un Facturado pasa a Entregado; la cobranza no cambia."""
    id_ = aprobado(v, ("TER-IPA-330", "24", "12"))
    entregar = caso_de_factura(uf.EntregarPedido)
    with pytest.raises(PedidoInvalido, match="El pedido está aprobado"):
        entregar.ejecutar(v["actor"], id_)
    facturar(v, id_)
    entregar.ejecutar(v["actor"], id_)
    p = Pedido.objects.get(pk=id_)
    assert (p.estado, p.entregado_por_id) == ("ENTREGADO", v["actor"].usuario_id)
    assert p.entregado_en is not None and p.cobranza.estado == "PENDIENTE"


@pytest.mark.django_db(transaction=True)
def test_dos_facturaciones_por_el_ultimo_stock(empresa_ventas):
    """RF-VEN-26: dos usuarios facturan a la vez; solo uno saca el stock."""
    empresa, actor = empresa_ventas
    v = preparar(empresa, actor)
    pedidos = [aprobado(v, ("TER-IPA-330", "1010", "12")) for _ in range(2)]
    barrera, resultados = threading.Barrier(2), []

    def facturar_en_hilo(pedido_id):
        try:
            with tenant_context(empresa.id):
                barrera.wait(timeout=5)
                facturar(v, pedido_id)
            resultados.append("ok")
        except PedidoInvalido as e:
            resultados.append(e.mensaje)
        finally:
            connection.close()

    hilos = [threading.Thread(target=facturar_en_hilo, args=(p,)) for p in pedidos]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=15)
    assert sorted(resultados) == ["Stock insuficiente: TER-IPA-330 faltan 1010.0000", "ok"]
    assert sorted(Pedido.objects.values_list("estado", flat=True)) == ["APROBADO", "FACTURADO"]
    assert inventario().disponibles([v["ids"]["TER-IPA-330"]], HOY)[v["ids"]["TER-IPA-330"]] == 0
