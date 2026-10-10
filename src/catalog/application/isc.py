"""Categorías y tarifas de ISC por empresa (UC-CAT-05; RF-CAT-22 a 24, 28; RN-CAT-10)."""

from datetime import date
from decimal import Decimal
from typing import Protocol

from catalog.domain.errores import IscInvalido
from shared.application.autorizacion import Actor, CasoDeUso

GESTIONAR = "catalogo.isc.gestionar"


class IscRepo(Protocol):
    def existe_categoria(self, nombre: str) -> bool: ...
    def crear_categoria(self, nombre: str, codigo_tipo_sistema: str) -> int: ...
    def categoria_existe(self, categoria_id: int) -> bool: ...
    def existe_tarifa(self, categoria_id: int, desde: date) -> bool: ...
    def agregar_tarifa(
        self, categoria_id: int, monto: Decimal, desde: date, actor_id: int
    ) -> None: ...
    def productos_activos_con_categoria(self, categoria_id: int) -> int: ...
    def cambiar_estado_categoria(self, categoria_id: int, activo: bool) -> None: ...


class _BaseIsc(CasoDeUso):
    permiso_requerido = GESTIONAR

    def __init__(self, repo: IscRepo, atomic):
        self._repo = repo
        self._atomic = atomic

    def _agregar(self, actor: Actor, categoria_id: int, monto: Decimal, desde: date) -> None:
        if monto is None or monto <= 0:
            raise IscInvalido("El monto por litro debe ser mayor a 0")
        if desde is None:
            raise IscInvalido("La fecha de vigencia es obligatoria")
        if self._repo.existe_tarifa(categoria_id, desde):
            raise IscInvalido(f"Ya hay una tarifa vigente desde {desde:%Y-%m-%d}")
        self._repo.agregar_tarifa(categoria_id, monto, desde, actor.usuario_id)


class CrearCategoriaIsc(_BaseIsc):
    """Nombre, código de tipo de sistema y primera tarifa (RF-CAT-22, 23)."""

    def ejecutar(
        self, actor: Actor, nombre: str, codigo_tipo_sistema: str, monto: Decimal, desde: date
    ) -> int:
        nombre, codigo = nombre.strip(), codigo_tipo_sistema.strip()
        if not nombre or not codigo:
            raise IscInvalido("Nombre y código de tipo de sistema son obligatorios")
        if self._repo.existe_categoria(nombre):
            raise IscInvalido(f"Ya existe la categoría de ISC {nombre}")
        with self._atomic():
            categoria_id = self._repo.crear_categoria(nombre, codigo)
            self._agregar(actor, categoria_id, monto, desde)
            return categoria_id


class AgregarTarifaIsc(_BaseIsc):
    """Un cambio de tarifa es una tarifa nueva; las existentes no se editan (RF-CAT-24)."""

    def ejecutar(self, actor: Actor, categoria_id: int, monto: Decimal, desde: date) -> None:
        if not self._repo.categoria_existe(categoria_id):
            raise IscInvalido("La categoría de ISC no existe")
        self._agregar(actor, categoria_id, monto, desde)


class CambiarEstadoCategoriaIsc(_BaseIsc):
    def ejecutar(self, actor: Actor, categoria_id: int, activo: bool) -> None:
        if not self._repo.categoria_existe(categoria_id):
            raise IscInvalido("La categoría de ISC no existe")
        if not activo and (n := self._repo.productos_activos_con_categoria(categoria_id)):
            raise IscInvalido(  # RF-CAT-28
                f"La categoría está asignada a {n} productos activos; cámbialos primero"
            )
        self._repo.cambiar_estado_categoria(categoria_id, activo)
