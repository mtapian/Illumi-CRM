"""0005a: casos de uso de la OP. T4: crear, editar, pasar a en proceso y anular (RF-PRD-16, 18,
33, 35 a 38, 44, 45)."""

from dataclasses import replace
from datetime import date
from decimal import Decimal as D

import pytest

from catalog.infrastructure.models import Producto, RecetaComponente, Unidad
from inventory.infrastructure.models import Almacen, Movimiento
from production.application import ordenes as uc
from production.domain.errores import OpInvalida
from production.domain.op import Componente
from production.infrastructure.contenedor import caso_de_op
from production.infrastructure.models import OpComponente, OrdenProduccion
from shared.application.autorizacion import Actor
from shared.domain.errores import AccesoDenegado
from tenancy.infrastructure.models import Usuario
from tests.conftest import asignar_rol

pytestmark = pytest.mark.django_db
HOY = date(2026, 10, 12)


@pytest.fixture
def prod(empresa_produccion):
    """GRA-IPA con receta (malta 0.2 kg por litro) y un servicio de maquila."""
    _, actor = empresa_produccion
    granel, malta = Producto.objects.get(sku="GRA-IPA"), Producto.objects.get(sku="INS-MALTA")
    RecetaComponente.objects.create(producto=granel, componente=malta, cantidad_por_unidad=D("0.2"))
    maquila = Producto.objects.create(
        sku="SRV-MAQ",
        nombre="Maquila",
        tipo="SERVICIO",
        se_compra=True,
        unidad=Unidad.objects.get(abreviatura="SERV"),
    )
    almacen = Almacen.objects.get(nombre="Principal").id
    datos = uc.DatosOp(granel.id, D("500"), HOY, almacen, almacen, comentario="Bar Central")
    return actor, datos, {"granel": granel.id, "malta": malta.id, "maquila": maquila.id}


def crear(actor, datos, usar_receta=True):
    return caso_de_op(uc.CrearOp).ejecutar(actor, datos, usar_receta)


def componentes(op_id):
    filas = OpComponente.objects.filter(op_id=op_id).order_by("id")
    return [(c.producto_id, c.por_consumir, c.costo_servicio) for c in filas]


def test_crear_copia_la_receta_sin_mover_stock(prod):
    """RF-PRD-35, 36, 37."""
    actor, datos, ids = prod
    op_id = crear(actor, datos)
    op = OrdenProduccion.objects.get(pk=op_id)
    assert (op.numero, op.estado, op.responsable_id, op.comentario) == (
        1,
        "CREADA",
        actor.usuario_id,
        "Bar Central",
    )
    assert componentes(op_id) == [(ids["malta"], D("100.0000"), None)]
    assert not Movimiento.objects.exists()
    assert componentes(crear(actor, datos, usar_receta=False)) == []
    assert OrdenProduccion.objects.get(numero=2)


@pytest.mark.parametrize(
    "cambio, mensaje",
    [
        ({"producto_id": "malta"}, "Elige un bien activo que se fabrique"),
        ({"cantidad": D("0")}, "La cantidad debe ser mayor a 0"),
        (
            {"responsable_id": "otro"},
            "El responsable debe ser un usuario activo que pueda ejecutar OP",
        ),
    ],
)
def test_crear_rechaza(prod, empresa_produccion, cambio, mensaje):
    actor, datos, ids = prod
    otro = Usuario.objects.create_user("ana@andina.pe", "x", empresa=empresa_produccion[0])
    asignar_rol(otro, "Ventas")
    valores = {"malta": ids["malta"], "otro": otro.id}
    cambio = {k: valores.get(v, v) if isinstance(v, str) else v for k, v in cambio.items()}
    with pytest.raises(OpInvalida, match=mensaje):
        crear(actor, replace(datos, **cambio))


def test_editar_componentes_con_servicio_y_sin_tocar_la_receta(prod):
    """RF-PRD-38 y RF-PRD-44: cualquier producto activo; un servicio lleva su costo."""
    actor, datos, ids = prod
    op_id = crear(actor, datos)
    lista = (Componente(ids["malta"], D("102")), Componente(ids["maquila"], D("1"), D("80")))
    caso_de_op(uc.EditarOp).ejecutar(actor, op_id, replace(datos, componentes=lista))
    assert componentes(op_id) == [
        (ids["malta"], D("102.0000"), None),
        (ids["maquila"], D("1.0000"), D("80.00")),
    ]
    assert RecetaComponente.objects.get().cantidad_por_unidad == D("0.2000")
    with pytest.raises(OpInvalida, match="Indica el costo del servicio SRV-MAQ"):
        sin_costo = (Componente(ids["maquila"], D("1")),)
        caso_de_op(uc.EditarOp).ejecutar(actor, op_id, replace(datos, componentes=sin_costo))


def test_en_proceso_editable_y_anular_sin_stock(prod):
    """RF-PRD-16, RF-PRD-33 y RF-PRD-45: en proceso solo cambia el estado."""
    actor, datos, ids = prod
    op_id = crear(actor, datos)
    caso_de_op(uc.PasarAEnProceso).ejecutar(actor, op_id)
    op = OrdenProduccion.objects.get(pk=op_id)
    assert (op.estado, op.en_proceso_por_id) == ("EN_PROCESO", actor.usuario_id)
    with pytest.raises(OpInvalida, match="La OP ya está en proceso"):
        caso_de_op(uc.PasarAEnProceso).ejecutar(actor, op_id)
    caso_de_op(uc.EditarOp).ejecutar(actor, op_id, replace(datos, cantidad=D("400")))
    with pytest.raises(OpInvalida, match="Indica el motivo de la anulación"):
        caso_de_op(uc.AnularOp).ejecutar(actor, op_id, " ")
    caso_de_op(uc.AnularOp).ejecutar(actor, op_id, "Se canceló la cocción")
    op.refresh_from_db()
    assert (op.estado, op.cantidad, op.motivo_anulacion) == (
        "ANULADA",
        D("400.0000"),
        "Se canceló la cocción",
    )
    assert not Movimiento.objects.exists()
    with pytest.raises(OpInvalida, match="La OP está anulada"):
        caso_de_op(uc.EditarOp).ejecutar(actor, op_id, datos)


def test_permisos(prod):
    """Crear y editar: planificar; en proceso y finalizar: ejecutar; anular: anular."""
    actor, datos, _ = prod
    op_id = crear(actor, datos)
    sin = Actor(actor.usuario_id, actor.empresa_id, actor.permisos - {uc.ANULAR, uc.PLANIFICAR})
    with pytest.raises(AccesoDenegado):
        caso_de_op(uc.AnularOp).ejecutar(sin, op_id, "x")
    with pytest.raises(AccesoDenegado):
        crear(sin, datos)
    caso_de_op(uc.PasarAEnProceso).ejecutar(sin, op_id)


def test_las_op_en_curso_cuentan_para_el_aviso_de_la_plataforma(prod):
    """RF-TEN-32 (0001b): deshabilitar producción advierte las OP Creadas o En proceso."""
    from tenancy.application.operaciones_en_curso import contadores

    actor, datos, _ = prod
    crear(actor, datos)
    caso_de_op(uc.AnularOp).ejecutar(actor, crear(actor, datos), "x")
    assert contadores.advertencias(actor.empresa_id, {"produccion.op"}) == [
        "La empresa tiene 1 OP en curso; quedarán sin poder operarse"
    ]
