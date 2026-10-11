"""Ajustes de inventario (UC-INV-04, spec 0003b; RF-INV-08 a 13, 27 a 29)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from inventory.application.servicio import InventarioService, Linea
from inventory.domain.ajuste import (
    CONTEO,
    CORRECCION,
    MERMA,
    SALDO_INICIAL,
    costo_de_entrada_ajuste,
    diferencia_conteo,
    validar_ajuste,
    validar_saldo_inicial,
)
from inventory.domain.errores import AjusteInvalido
from inventory.domain.existencia import ENTRADA, SALIDA
from shared.application.autorizacion import Actor, CasoDeUso
from shared.application.puertos import SequencePort
from shared.domain.errores import NoEncontrado

REGISTRAR, ANULAR = "inventario.ajuste.registrar", "inventario.ajuste.anular"
REF, ANULADO = "AJUSTE", "ANULADO"


@dataclass(frozen=True)
class LineaAjuste:
    producto_id: int
    cantidad: Decimal  # en CONTEO, lo contado
    costo: Decimal | None = None
    lote: str | None = None  # en CONTEO, None es el stock sin lote
    vencimiento: date | None = None
    sentido: str = ""  # ENTRADA o SALIDA, solo en CORRECCION


class AjustesRepo(Protocol):
    def crear(self, numero, tipo, motivo, almacen_id, destino_id, usuario_id) -> int: ...
    def agregar_linea(self, ajuste_id: int, linea: LineaAjuste, sistema) -> None: ...
    def estado(self, ajuste_id: int) -> str | None: ...  # bloquea la fila
    def anular(self, ajuste_id: int, usuario_id: int, motivo: str) -> None: ...


class _Base(CasoDeUso):
    def __init__(
        self,
        repo: AjustesRepo,
        inventario: InventarioService,
        secuencia: SequencePort,
        atomic: Callable,
    ):
        self._repo, self._inv, self._secuencia, self._atomic = repo, inventario, secuencia, atomic


class RegistrarAjuste(_Base):
    permiso_requerido = REGISTRAR

    def ejecutar(
        self,
        actor: Actor,
        tipo: str,
        almacen_id: int,
        motivo: str,
        lineas: list[LineaAjuste],
        destino_id: int | None,
        hoy: date,
    ) -> int:
        validar_ajuste(tipo, motivo, almacen_id, destino_id)
        if not lineas:
            raise AjusteInvalido("El ajuste necesita al menos una línea")
        with self._atomic():
            numero = self._secuencia.siguiente(REF)  # RF-INV-28
            ajuste = self._repo.crear(
                numero, tipo, motivo.strip(), almacen_id, destino_id, actor.usuario_id
            )
            self._inv.bloquear([x.producto_id for x in lineas])
            for x in lineas:
                sistema = self._aplicar(actor, tipo, ajuste, almacen_id, destino_id, x, hoy)
                self._repo.agregar_linea(ajuste, x, sistema)
        return ajuste

    def _aplicar(self, actor, tipo, ajuste, almacen_id, destino_id, x: LineaAjuste, hoy):
        """Mueve el stock de una línea según su tipo; devuelve el stock del sistema en un
        CONTEO (RF-INV-11)."""
        inv, usuario = self._inv, actor.usuario_id

        def linea(cantidad, costo=None, exacto=False):
            return Linea(x.producto_id, almacen_id, cantidad, costo, x.lote, x.vencimiento, exacto)

        def entra(cantidad, costo):
            inv.registrar_entrada(tipo, REF, ajuste, [linea(cantidad, costo)], usuario, hoy)

        def sale(cantidad, exacto=False):
            inv.registrar_salida(tipo, REF, ajuste, [linea(cantidad, exacto=exacto)], usuario, hoy)

        if tipo == SALDO_INICIAL:
            validar_saldo_inicial(x.costo, inv.tiene_movimientos(x.producto_id))
            entra(x.cantidad, x.costo)
        elif tipo == MERMA:
            sale(x.cantidad)
        elif tipo == CORRECCION:
            if x.sentido == ENTRADA:
                promedio = inv.promedio_vigente(x.producto_id)
                entra(x.cantidad, costo_de_entrada_ajuste(tipo, x.costo, promedio))
            elif x.sentido == SALIDA:
                sale(x.cantidad)
            else:
                raise AjusteInvalido("Indica si la corrección es entrada o salida")
        elif tipo == CONTEO:
            sistema = inv.stock_en(x.producto_id, almacen_id, x.lote)
            diferencia = diferencia_conteo(sistema, x.cantidad)
            if diferencia > 0:
                promedio = inv.promedio_vigente(x.producto_id)
                entra(diferencia, costo_de_entrada_ajuste(tipo, x.costo, promedio))
            elif diferencia < 0:
                sale(-diferencia, exacto=True)  # de esa existencia, no por FEFO
            return sistema
        else:  # TRANSFERENCIA
            inv.transferir(REF, ajuste, [linea(x.cantidad)], destino_id, usuario, hoy)
        return None


class AnularAjuste(_Base):
    """RF-INV-13: inversos al costo original (RF-INV-20); una sola vez."""

    permiso_requerido = ANULAR

    def ejecutar(self, actor: Actor, ajuste_id: int, motivo: str) -> None:
        if not motivo.strip():
            raise AjusteInvalido("El motivo es obligatorio")
        with self._atomic():
            estado = self._repo.estado(ajuste_id)
            if estado is None:
                raise NoEncontrado("El ajuste no existe")
            if estado == ANULADO:
                raise AjusteInvalido("El ajuste ya está anulado")
            self._inv.revertir(REF, ajuste_id, actor.usuario_id)
            self._repo.anular(ajuste_id, actor.usuario_id, motivo.strip())
