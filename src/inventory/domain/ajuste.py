"""Ajustes de inventario (spec 0003b; RF-INV-08, 09, 11, 12, 27)."""

from decimal import Decimal

from inventory.domain.errores import AjusteInvalido, CostoRequerido

SALDO_INICIAL, CONTEO, MERMA = "SALDO_INICIAL", "CONTEO", "MERMA"
CORRECCION, TRANSFERENCIA = "CORRECCION", "TRANSFERENCIA"
TIPOS = (SALDO_INICIAL, CONTEO, MERMA, CORRECCION, TRANSFERENCIA)


def validar_ajuste(tipo: str, motivo: str, origen: int, destino: int | None) -> None:
    """RF-INV-08: motivo obligatorio. RF-INV-12: destino solo en transferencias y distinto."""
    if tipo not in TIPOS:
        raise AjusteInvalido("Tipo de ajuste desconocido")
    if not motivo.strip():
        raise AjusteInvalido("El motivo es obligatorio")
    if tipo == TRANSFERENCIA and (destino is None or destino == origen):
        raise AjusteInvalido("La transferencia necesita un almacén destino distinto del origen")
    if tipo != TRANSFERENCIA and destino is not None:
        raise AjusteInvalido("Solo una transferencia tiene almacén destino")


def validar_saldo_inicial(costo: Decimal | None, tiene_movimientos: bool) -> None:
    """RF-INV-09 (RN-INV-08): costo > 0 y solo para la apertura del producto."""
    if costo is None or costo <= 0:
        raise AjusteInvalido("El saldo inicial requiere un costo unitario mayor a 0")
    if tiene_movimientos:
        raise AjusteInvalido(
            "El producto ya tiene movimientos: el saldo inicial solo sirve para la apertura"
        )


def diferencia_conteo(sistema: Decimal, contado: Decimal) -> Decimal:
    """RF-INV-11: contado − sistema; 0 no genera movimiento."""
    return contado - sistema


def costo_de_entrada_ajuste(
    tipo: str, ingresado: Decimal | None, promedio: Decimal | None
) -> Decimal:
    """Costo de una entrada por ajuste (tabla de Definiciones). `promedio=None`: el producto
    nunca tuvo costo, así que hay que ingresarlo (RF-INV-27)."""
    if tipo == SALDO_INICIAL or ingresado is not None:
        return ingresado
    if promedio is None:
        raise CostoRequerido("El producto nunca tuvo costo: ingresa el costo unitario")
    return promedio
