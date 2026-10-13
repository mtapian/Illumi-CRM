"""Pagos de una cobranza y métodos de pago (spec 0006b, UC-VEN-09 y 10)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from sales.domain import cobranza as dom
from sales.domain.errores import CobranzaInvalida
from shared.application.autorizacion import Actor, CasoDeUso

VER = "ventas.cobranza.ver"
GESTIONAR = "ventas.cobranza.gestionar"
ANULAR = "ventas.cobranza.anular"  # segregación de funciones (RF-VEN-61)
METODOS = "ventas.metodo_pago.gestionar"  # RF-VEN-64


@dataclass(frozen=True)
class DatosPago:
    metodo_id: int
    monto: Decimal
    fecha: date
    referencia: str = ""


class CobranzasRepo(Protocol):
    # estado, total, pagado y emisión; FOR UPDATE
    def bloquear(self, cobranza_id: int) -> tuple[str, Decimal, Decimal, date]: ...
    def metodo_activo(self, metodo_id: int) -> bool: ...
    def registrar_pago(self, cobranza_id: int, datos: DatosPago, usuario_id: int) -> int: ...
    def actualizar(self, cobranza_id: int, pagado: Decimal, estado: str) -> None: ...
    def pago(self, pago_id: int) -> tuple[int, Decimal, bool]: ...  # cobranza, monto, anulado
    def anular_pago(self, pago_id: int, usuario_id: int, motivo: str) -> None: ...
    def existe_metodo(self, nombre: str, excluir: int | None) -> bool: ...
    def guardar_metodo(self, metodo_id: int | None, nombre: str) -> int: ...
    def estado_metodo(self, metodo_id: int, activo: bool) -> None: ...


class _Base(CasoDeUso):
    permiso_requerido = GESTIONAR

    def __init__(self, repo: CobranzasRepo, atomic: Callable):
        self._repo, self._atomic = repo, atomic


class RegistrarPago(_Base):
    """RF-VEN-54, 55 y 57: nunca mayor al saldo; Parcial mientras quede saldo, luego Pagada."""

    def ejecutar(self, actor: Actor, cobranza_id: int, datos: DatosPago, hoy: date) -> int:
        with self._atomic():
            return self.registrar(actor, cobranza_id, datos, hoy)

    def registrar(self, actor: Actor, cobranza_id: int, datos: DatosPago, hoy: date) -> int:
        """Dentro de una transacción abierta (también la usa la venta directa)."""
        if datos.fecha > hoy:
            raise CobranzaInvalida("La fecha del pago no puede ser futura", "fecha")
        if not self._repo.metodo_activo(datos.metodo_id):
            raise CobranzaInvalida("El método de pago no existe o está inactivo", "metodo")
        estado, total, pagado, emision = self._repo.bloquear(cobranza_id)
        if datos.fecha < emision:
            raise CobranzaInvalida(
                f"La fecha del pago no puede ser anterior a la emisión ({emision:%Y-%m-%d})",
                "fecha",
            )
        dom.validar_pago(estado, datos.monto, total - pagado)
        datos = DatosPago(datos.metodo_id, datos.monto, datos.fecha, datos.referencia.strip())
        pago_id = self._repo.registrar_pago(cobranza_id, datos, actor.usuario_id)
        pagado += datos.monto
        self._repo.actualizar(cobranza_id, pagado, dom.estado(total, pagado))
        return pago_id


class AnularPago(_Base):
    """RF-VEN-56 y 61: con motivo, una sola vez; el estado se recalcula (Parcial o Pendiente).
    Quien registra pagos no los anula (permiso propio)."""

    permiso_requerido = ANULAR

    def ejecutar(self, actor: Actor, pago_id: int, motivo: str) -> None:
        if not motivo.strip():
            raise CobranzaInvalida("Indica el motivo de la anulación", "motivo")
        with self._atomic():
            cobranza_id, _, _ = self._repo.pago(pago_id)
            _, total, pagado, _ = self._repo.bloquear(cobranza_id)
            _, monto, anulado = self._repo.pago(pago_id)  # releído con la cobranza bloqueada
            if anulado:
                raise CobranzaInvalida("El pago ya está anulado")
            self._repo.anular_pago(pago_id, actor.usuario_id, motivo.strip())
            pagado -= monto
            self._repo.actualizar(cobranza_id, pagado, dom.estado(total, pagado))


class GuardarMetodoPago(_Base):
    """RF-VEN-59 y 64: crear o renombrar; nombre único sin mayúsculas."""

    permiso_requerido = METODOS

    def ejecutar(self, actor: Actor, metodo_id: int | None, nombre: str) -> int:
        nombre = nombre.strip()
        if not nombre:
            raise CobranzaInvalida("Indica el nombre", "nombre")
        with self._atomic():
            if self._repo.existe_metodo(nombre, metodo_id):
                raise CobranzaInvalida("Ya existe un método de pago con ese nombre", "nombre")
            return self._repo.guardar_metodo(metodo_id, nombre)


class CambiarEstadoMetodoPago(_Base):
    """RF-VEN-59 y 64: no se elimina; inactivo no se ofrece en pagos nuevos."""

    permiso_requerido = METODOS

    def ejecutar(self, actor: Actor, metodo_id: int, activo: bool) -> None:
        self._repo.estado_metodo(metodo_id, activo)
