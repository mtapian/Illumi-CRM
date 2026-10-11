"""Almacenes (UC-INV-01; RF-INV-02, RF-INV-03)."""

from typing import Protocol

from inventory.domain.errores import AlmacenInvalido
from shared.application.autorizacion import Actor, CasoDeUso
from shared.domain.errores import NoEncontrado

GESTIONAR = "inventario.almacen.gestionar"


class AlmacenesRepo(Protocol):
    def existe(self, almacen_id: int) -> bool: ...
    def existe_nombre(self, nombre: str, excluir: int | None) -> bool: ...
    def guardar(self, almacen_id: int | None, nombre: str) -> int: ...
    def tiene_stock(self, almacen_id: int) -> bool: ...
    def cambiar_estado(self, almacen_id: int, activo: bool) -> None: ...


class _Base(CasoDeUso):
    permiso_requerido = GESTIONAR

    def __init__(self, repo: AlmacenesRepo):
        self._repo = repo

    def _existe(self, almacen_id: int) -> None:
        if not self._repo.existe(almacen_id):
            raise NoEncontrado("El almacén no existe")


class GuardarAlmacen(_Base):
    """Crea (`almacen_id=None`) o renombra; nombre único en la empresa, sin mayúsculas."""

    def ejecutar(self, actor: Actor, almacen_id: int | None, nombre: str) -> int:
        if almacen_id is not None:
            self._existe(almacen_id)
        nombre = nombre.strip()
        if not nombre:
            raise AlmacenInvalido("El nombre del almacén es obligatorio")
        if self._repo.existe_nombre(nombre, almacen_id):
            raise AlmacenInvalido(f"Ya existe el almacén {nombre}")
        return self._repo.guardar(almacen_id, nombre)


class CambiarEstadoAlmacen(_Base):
    """RF-INV-03: un almacén con stock no se desactiva."""

    def ejecutar(self, actor: Actor, almacen_id: int, activo: bool) -> None:
        self._existe(almacen_id)
        if not activo and self._repo.tiene_stock(almacen_id):
            raise AlmacenInvalido("El almacén tiene stock")
        self._repo.cambiar_estado(almacen_id, activo)
