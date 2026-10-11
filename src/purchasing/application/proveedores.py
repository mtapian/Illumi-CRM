"""Proveedores y proveedores del producto (UC-COM-01 y UC-COM-08, spec 0002d)."""

from collections.abc import Callable
from decimal import Decimal
from typing import Protocol

from catalog.application.fachada import CatalogoQuery
from purchasing.application.puertos import Puertos
from purchasing.domain.errores import ProveedorInvalido
from purchasing.domain.proveedor import (
    DatosProveedor,
    validar_proveedor,
    validar_proveedor_producto,
)
from shared.application.autorizacion import Actor, CasoDeUso
from shared.domain.errores import NoEncontrado

GESTIONAR = "compras.proveedor.gestionar"
NO_EXISTE = "El proveedor no existe"


class ProveedoresRepo(Protocol):
    def activo(self, proveedor_id: int) -> bool | None: ...  # None: no existe en la empresa
    def existe_documento(self, tipo: str, numero: str, excluir: int | None) -> bool: ...
    def guardar(self, proveedor_id: int | None, datos: DatosProveedor) -> int: ...
    def cambiar_estado(self, proveedor_id: int, activo: bool) -> None: ...
    def eliminar(self, proveedor_id: int) -> None: ...
    def asociar(self, proveedor_id, producto_id, precio, plazo, codigo) -> None: ...
    def quitar(self, proveedor_id: int, producto_id: int) -> None: ...


class _Base(CasoDeUso):
    permiso_requerido = GESTIONAR

    def __init__(self, repo: ProveedoresRepo, puertos: Puertos, catalogo: CatalogoQuery, atomic):
        self._repo, self._puertos, self._catalogo = repo, puertos, catalogo
        self._atomic: Callable = atomic

    def _activo(self, proveedor_id: int) -> bool:
        activo = self._repo.activo(proveedor_id)
        if activo is None:
            raise NoEncontrado(NO_EXISTE)
        return activo


class GuardarProveedor(_Base):
    """Crea (`proveedor_id=None`) o edita un proveedor (RF-COM-01)."""

    def ejecutar(self, actor: Actor, proveedor_id: int | None, datos: DatosProveedor) -> int:
        if proveedor_id is not None:
            self._activo(proveedor_id)
        datos = validar_proveedor(datos)
        if self._repo.existe_documento(datos.tipo_doc, datos.num_doc, proveedor_id):
            raise ProveedorInvalido(
                f"Ya existe un proveedor con el {datos.tipo_doc} {datos.num_doc}"
            )
        return self._repo.guardar(proveedor_id, datos)


class CambiarEstadoProveedor(_Base):
    """RF-COM-03: desactivado no se ofrece en compras nuevas ni para asociarlo."""

    def ejecutar(self, actor: Actor, proveedor_id: int, activo: bool) -> None:
        self._activo(proveedor_id)
        self._repo.cambiar_estado(proveedor_id, activo)


class EliminarProveedor(_Base):
    def ejecutar(self, actor: Actor, proveedor_id: int) -> None:
        self._activo(proveedor_id)
        if self._puertos.compras.tiene_compras(proveedor_id):  # RF-COM-02
            raise ProveedorInvalido("El proveedor tiene compras; puedes desactivarlo")
        self._repo.eliminar(proveedor_id)


class AsociarProveedorProducto(_Base):
    """RF-COM-21: crea o actualiza precio referencial, plazo y código del proveedor."""

    def ejecutar(
        self,
        actor: Actor,
        proveedor_id: int,
        producto_id: int,
        precio: Decimal,
        plazo: int,
        codigo: str = "",
    ) -> None:
        if not self._activo(proveedor_id):
            raise ProveedorInvalido("El proveedor está desactivado")
        producto = self._catalogo.producto(producto_id)
        if producto is None:
            raise NoEncontrado("El producto no existe")
        precio = validar_proveedor_producto(producto.se_compra, precio, plazo)
        self._repo.asociar(proveedor_id, producto_id, precio, plazo, codigo.strip())


class QuitarProveedorProducto(_Base):
    """RF-COM-22: no afecta las compras ya registradas."""

    def ejecutar(self, actor: Actor, proveedor_id: int, producto_id: int) -> None:
        self._repo.quitar(proveedor_id, producto_id)
