"""Pedido de venta (spec 0006a; constitución, art. 10): Creado ▸ Aprobado ▸ Facturado ▸
Entregado, y Cancelado. Facturar y entregar son de 0006b."""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sales.domain.errores import PedidoInvalido

CREADO, APROBADO, FACTURADO, ENTREGADO, CANCELADO = (
    "CREADO",
    "APROBADO",
    "FACTURADO",
    "ENTREGADO",
    "CANCELADO",
)
ESTADOS = (CREADO, APROBADO, FACTURADO, ENTREGADO, CANCELADO)
NOMBRES = {
    CREADO: "creado",
    APROBADO: "aprobado",
    FACTURADO: "facturado",
    ENTREGADO: "entregado",
    CANCELADO: "cancelado",
}
GENERICO = "Clientes varios"  # RF-VEN-03
SIN_DOCUMENTO = "SD"
CENTIMO = Decimal("0.01")
# (estado, acción) → estado nuevo (tabla de estados de la spec; RF-VEN-16)
TRANSICIONES = {
    (CREADO, "editar"): CREADO,
    (CREADO, "aprobar"): APROBADO,
    (APROBADO, "editar_fecha"): APROBADO,  # fecha de entrega y comentario (RF-VEN-11)
    (APROBADO, "facturar"): FACTURADO,
    (FACTURADO, "entregar"): ENTREGADO,
    (CREADO, "cancelar"): CANCELADO,
    (APROBADO, "cancelar"): CANCELADO,
}


@dataclass(frozen=True)
class LineaPedido:
    producto_id: int
    cantidad: Decimal
    precio: Decimal  # unitario, con impuestos (0002e)


def numero_pedido(n: int) -> str:
    return f"P-{n:06d}"


def transicion(estado: str, accion: str) -> str:
    if (estado, accion) in TRANSICIONES:
        return TRANSICIONES[estado, accion]
    if estado == APROBADO and accion == "editar":  # RF-VEN-11 (RN-VEN-06)
        raise PedidoInvalido(
            "El pedido está aprobado: cancélalo y crea otro para cambiar sus líneas", "lineas"
        )
    if accion == "facturar":
        raise PedidoInvalido("El pedido debe estar aprobado para facturarlo")
    if estado == accion_destino(accion):
        raise PedidoInvalido(f"El pedido ya está {NOMBRES[estado]}")
    raise PedidoInvalido(f"El pedido está {NOMBRES[estado]}")


def accion_destino(accion: str) -> str | None:
    return {"aprobar": APROBADO, "entregar": ENTREGADO, "cancelar": CANCELADO}.get(accion)


def validar_lineas(lineas, para_aprobar: bool = False) -> None:
    """RF-VEN-06, 08: cantidad y precio mayores a 0; un producto por línea."""
    if para_aprobar and not lineas:
        raise PedidoInvalido("El pedido no tiene líneas", "lineas")
    ids = [x.producto_id for x in lineas]
    if len(set(ids)) != len(ids):
        raise PedidoInvalido("Un producto está repetido en el pedido", "lineas")
    if any(x.cantidad <= 0 for x in lineas):
        raise PedidoInvalido("La cantidad debe ser mayor a 0", "lineas")
    if any(x.precio <= 0 for x in lineas):
        raise PedidoInvalido("El precio debe ser mayor a 0", "lineas")


def subtotal(x: LineaPedido) -> Decimal:
    return (x.cantidad * x.precio).quantize(CENTIMO, ROUND_HALF_UP)


def total(lineas) -> Decimal:
    """RF-VEN-48: los precios ya incluyen impuestos; half-up por línea."""
    return sum((subtotal(x) for x in lineas), Decimal("0.00"))


def faltante(cantidad: Decimal, disponible: Decimal, es_servicio: bool) -> Decimal:
    """RF-VEN-45: un servicio no lleva stock."""
    return Decimal("0") if es_servicio else max(Decimal("0"), cantidad - disponible)


def indicadores(estado: str, fecha_entrega: date, faltantes, hoy: date) -> list[str]:
    """RF-VEN-15, 45, 46: Atrasado, Quiebre de stock y Listo para facturar."""
    marcas = []
    if estado in (CREADO, APROBADO, FACTURADO) and fecha_entrega < hoy:
        marcas.append("Atrasado")
    if estado in (CREADO, APROBADO):
        if any(f > 0 for f in faltantes):
            marcas.append("Quiebre de stock")
        elif estado == APROBADO:
            marcas.append("Listo para facturar")
    return marcas
