"""Maestro de impuestos de venta y de compra con tasas por vigencia (spec 0002e, UC-CAT-09)."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Protocol

from catalog.domain.errores import ImpuestoInvalido
from catalog.domain.impuestos import (
    COMPRA,
    EXO,
    IGV,
    INA,
    NOMBRE_TIPO,
    VENTA,
    criterio_sugerido,
    validar_impuesto,
    validar_tasa,
)
from shared.application.autorizacion import Actor, CasoDeUso

GESTIONAR = "catalogo.isc.gestionar"  # etiqueta "Gestionar impuestos" (plan §1)
# RF-CAT-52: (nombre, código) de cada tipo; el IGV toma la tasa vigente de la plataforma.
INICIALES = [("IGV 18%", IGV), ("Exonerado", EXO), ("Inafecto", INA)]
TIPOS = (VENTA, COMPRA)


class ImpuestosRepo(Protocol):
    def impuesto(self, id_: int) -> tuple[str, str, str]: ...  # (tipo, código, criterio); 404
    def existe_nombre(self, tipo: str, nombre: str, excluir_id: int | None) -> bool: ...
    def en_uso(self, id_: int) -> bool: ...
    def asignado_a_activos(self, id_: int) -> bool: ...
    def guardar(self, id_: int | None, nombre: str, tipo: str, codigo: str, criterio: str): ...
    def fechas_tasas(self, id_: int) -> list[date]: ...
    def agregar_tasa(self, id_: int, importe: Decimal, desde: date, actor_id: int): ...
    def cambiar_estado(self, id_: int, activo: bool) -> None: ...


class _Base(CasoDeUso):
    permiso_requerido = GESTIONAR

    def __init__(self, repo: ImpuestosRepo, atomic: Callable):
        self._repo = repo
        self._atomic = atomic


class GuardarImpuesto(_Base):
    """RF-CAT-53: nombre único por tipo; tipo, código y criterio fijos si un producto lo usa.
    Sin criterio, el sugerido por el código (enmienda 1)."""

    def ejecutar(
        self,
        actor: Actor,
        id_: int | None,
        nombre: str,
        tipo: str,
        codigo: str,
        criterio: str | None = None,
    ):
        nombre, criterio = nombre.strip(), criterio or criterio_sugerido(codigo)
        if not nombre:
            raise ImpuestoInvalido("El nombre del impuesto es obligatorio", "nombre")
        validar_impuesto(tipo, codigo, criterio)
        with self._atomic():
            if id_ is not None and self._repo.impuesto(id_) != (tipo, codigo, criterio):
                if self._repo.en_uso(id_):
                    raise ImpuestoInvalido(
                        "El impuesto está en uso: su tipo, código y criterio no se pueden cambiar",
                        "codigo",
                    )
            if self._repo.existe_nombre(tipo, nombre, id_):
                raise ImpuestoInvalido(
                    f"Ya existe el impuesto de {NOMBRE_TIPO[tipo]} {nombre}", "nombre"
                )
            return self._repo.guardar(id_, nombre, tipo, codigo, criterio)


class AgregarTasa(_Base):
    """RF-CAT-54: un cambio es una tasa nueva; las anteriores no se editan ni se borran."""

    def ejecutar(self, actor: Actor, id_: int, importe: Decimal, desde: date) -> None:
        with self._atomic():
            _, codigo, _ = self._repo.impuesto(id_)
            validar_tasa(codigo, importe, self._repo.fechas_tasas(id_), desde)
            self._repo.agregar_tasa(id_, importe, desde, actor.usuario_id)


class CambiarEstadoImpuesto(_Base):
    """RF-CAT-55: no se desactiva si lo usan productos activos."""

    def ejecutar(self, actor: Actor, id_: int, activo: bool) -> None:
        self._repo.impuesto(id_)
        if not activo and self._repo.asignado_a_activos(id_):
            raise ImpuestoInvalido("El impuesto está asignado a productos activos")
        self._repo.cambiar_estado(id_, activo)
