"""Arma los casos de uso de ventas con sus adaptadores reales."""

from datetime import date

from django.db import transaction
from django.db.models import Q

from catalog.infrastructure.contenedor import catalogo_query
from inventory.infrastructure.contenedor import inventario
from sales.domain.pedido import GENERICO, SIN_DOCUMENTO
from sales.infrastructure.models import Cliente
from sales.infrastructure.repositorios import ClientesOrm, PedidosOrm
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


def caso_de_pedido(clase):
    """`caso_de_pedido(pedidos.CrearPedido).ejecutar(actor, …)`."""
    return clase(
        PedidosOrm(), catalogo_query(), inventario(), SecuenciaPostgres(), transaction.atomic
    )
