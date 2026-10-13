"""Arma los casos de uso de ventas con sus adaptadores reales."""

from datetime import date

from django.db import transaction
from django.db.models import Q

from catalog.infrastructure.contenedor import catalogo_query
from inventory.infrastructure.contenedor import inventario
from sales.application import cobranzas, facturacion, pedidos
from sales.domain.pedido import GENERICO, SIN_DOCUMENTO
from sales.infrastructure.models import Cliente, MetodoPago
from sales.infrastructure.repositorios import (
    ClientesOrm,
    CobranzasOrm,
    FacturasOrm,
    PedidosOrm,
)
from shared.domain.tenant import tenant_context
from shared.infrastructure.secuencia import SecuenciaPostgres
from tenancy.infrastructure.contenedor import tenancy_service


def caso_de_cliente(clase):
    """`caso_de_cliente(clientes.GuardarCliente).ejecutar(actor, …)`."""
    return clase(ClientesOrm(), tenancy_service().reglas_documento, transaction.atomic)


def buscar_clientes(empresa_id: int, texto: str, limite: int = 10) -> list[Cliente]:
    """RF-VEN-50: activos cuyo nombre o número de documento contiene el texto."""
    texto = texto.strip()
    if not texto:
        return []
    with tenant_context(empresa_id):
        filas = Cliente.objects.filter(activo=True).filter(
            Q(nombre__icontains=texto) | Q(num_doc__icontains=texto)
        )
        return list(filas.order_by("nombre")[:limite])


def sembrar_cliente_generico(empresa_id: int, admin_id: int, hoy: date) -> None:
    """Sembrador de 0001a: "Clientes varios" (RF-VEN-03)."""
    Cliente.all_tenants.get_or_create(
        empresa_id=empresa_id,
        es_generico=True,
        defaults={"nombre": GENERICO, "tipo_doc": SIN_DOCUMENTO, "canal": "B2C"},
    )


METODOS_INICIALES = ("Efectivo", "Yape", "Plin", "Tarjeta", "Transferencia")


def sembrar_metodos_pago(empresa_id: int, admin_id: int | None, hoy: date) -> None:
    """Sembrador de 0001a: métodos de pago iniciales de la empresa (RF-VEN-58)."""
    for nombre in METODOS_INICIALES:
        MetodoPago.all_tenants.get_or_create(empresa_id=empresa_id, nombre=nombre)


def caso_de_pedido(clase):
    """`caso_de_pedido(pedidos.CrearPedido).ejecutar(actor, …)`."""
    return clase(
        PedidosOrm(), catalogo_query(), inventario(), SecuenciaPostgres(), transaction.atomic
    )


def caso_de_factura(clase):
    """`caso_de_factura(facturacion.FacturarPedido).ejecutar(actor, …)` (0006b)."""
    return clase(
        FacturasOrm(),
        catalogo_query(),
        inventario(),
        lambda fecha: tenancy_service().parametro_vigente("umbral_boleta_identificada", fecha),
        transaction.atomic,
    )


def caso_de_cobranza(clase):
    """`caso_de_cobranza(cobranzas.RegistrarPago).ejecutar(actor, …)` (0006b)."""
    return clase(CobranzasOrm(), transaction.atomic)


def metodos_activos() -> list[MetodoPago]:
    """Lo que se ofrece en un pago nuevo (RF-VEN-59), por nombre."""
    return list(MetodoPago.objects.filter(activo=True).order_by("nombre"))


def caso_de_venta_directa():
    """`caso_de_venta_directa().ejecutar(actor, datos, hoy)` (0006b, RF-VEN-18)."""
    return facturacion.VentaDirecta(
        FacturasOrm(),
        caso_de_pedido(pedidos.CrearPedido),
        caso_de_factura(facturacion.FacturarPedido),
        caso_de_cobranza(cobranzas.RegistrarPago),
        transaction.atomic,
    )
