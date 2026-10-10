"""Unidades, familias y productos (UC-CAT-01, 02 y 04; RF-CAT-01 a 14, 19 a 21)."""

from collections.abc import Callable
from dataclasses import replace
from typing import Protocol

from catalog.application.puertos import Puertos
from catalog.domain.errores import (
    CampoInmutable,
    ContenidoInmutable,
    LimiteProductosPlan,
    NoSePuedeDesactivar,
    NoSePuedeEliminar,
    PresentacionInvalida,
    ProductoInvalido,
    SkuDuplicado,
    UnidadInvalida,
)
from catalog.domain.presentacion import DatosPresentacion, validar_presentacion
from catalog.domain.producto import (
    DatosProducto,
    cabe_en_limite,
    cambios_prohibidos,
    puede_desactivar,
    puede_eliminar,
    validar_producto,
)
from catalog.domain.tipos import TipoProducto
from shared.application.autorizacion import Actor, CasoDeUso

GESTIONAR = "catalogo.producto.gestionar"
UNIDADES = "catalogo.unidad.gestionar"
INMUTABLE = "No se puede modificar SKU, tipo o unidad de un producto con movimientos"
CON_HISTORIAL = "El producto tiene historial; solo puede desactivarse"
UNIDADES_INICIALES = [  # RF-CAT-01: (nombre, abreviatura, código SUNAT)
    ("Unidad", "UND", "NIU"),
    ("Kilogramo", "KG", "KGM"),
    ("Gramo", "G", "GRM"),
    ("Litro", "L", "LTR"),
    ("Mililitro", "ML", "MLT"),
]


class CatalogoRepo(Protocol):
    """Todas las operaciones son de la empresa actual (TenantContext)."""

    def unidad_activa(self, abreviatura: str) -> int | None: ...
    def crear_unidad(self, nombre: str, abreviatura: str, codigo_sunat: str) -> int: ...
    def existe_unidad(self, abreviatura: str) -> bool: ...
    def unidad_en_uso(self, unidad_id: int, solo_activos: bool) -> bool: ...
    def cambiar_estado_unidad(self, unidad_id: int, activo: bool) -> None: ...
    def eliminar_unidad(self, unidad_id: int) -> None: ...
    def crear_familia(self, nombre: str) -> int: ...
    def existe_sku(self, sku: str, excluir_id: int | None = None) -> bool: ...
    def contar_activos(self) -> int: ...
    def producto(self, producto_id: int) -> DatosProducto: ...
    def crear_producto(self, datos: DatosProducto, unidad_id: int) -> int: ...
    def actualizar_producto(self, producto_id: int, datos: DatosProducto, unidad_id: int): ...
    def cambiar_estado_producto(self, producto_id: int, activo: bool) -> None: ...
    def eliminar_producto(self, producto_id: int) -> None: ...
    def granel_con_presentaciones_activas(self, producto_id: int) -> bool: ...
    def referencias_internas(self, producto_id: int) -> int:
        """Presentaciones que lo usan como granel o como material (0002b)."""
        ...

    def tipos_y_estado(self, ids) -> dict[int, tuple[TipoProducto, bool]]: ...
    def categoria_isc_activa(self, categoria_id: int) -> bool: ...
    def presentacion(self, producto_id: int) -> DatosPresentacion | None: ...
    def guardar_presentacion(self, producto_id: int, datos: DatosPresentacion) -> None: ...


class _Base(CasoDeUso):
    permiso_requerido = GESTIONAR

    def __init__(
        self,
        repo: CatalogoRepo,
        puertos: Puertos,
        limite_productos: Callable[[int], int | None],
        atomic: Callable,
    ):
        self._repo = repo
        self._puertos = puertos
        self._limite = limite_productos
        self._atomic = atomic

    def _unidad(self, abreviatura: str) -> int:
        unidad_id = self._repo.unidad_activa(abreviatura)
        if unidad_id is None:
            raise UnidadInvalida(f"La unidad {abreviatura} no existe o está inactiva")
        return unidad_id

    def _exigir_limite(self, empresa_id: int) -> None:
        # ponytail: sin lock; dos altas simultáneas en el último cupo podrían pasar ambas.
        limite = self._limite(empresa_id)
        if not cabe_en_limite(self._repo.contar_activos(), limite):
            raise LimiteProductosPlan(f"Tu plan permite hasta {limite} productos activos")

    def _validar_isc(self, d: DatosProducto) -> None:
        if d.isc_categoria_id and not self._repo.categoria_isc_activa(d.isc_categoria_id):
            raise ProductoInvalido("La categoría de ISC no existe o está inactiva")

    def _validar_presentacion(self, d: DatosProducto, p: DatosPresentacion | None) -> None:
        if d.tipo != TipoProducto.TERMINADO:
            return
        if p is None:
            raise PresentacionInvalida("Un terminado requiere su presentación")  # RF-CAT-05
        if len({m for m, _ in p.materiales}) != len(p.materiales):
            raise PresentacionInvalida("Un material está repetido en la presentación")
        tipos = self._repo.tipos_y_estado([p.granel_id, *(m for m, _ in p.materiales)])
        validar_presentacion(
            tipos.get(p.granel_id, (None, False)),
            p.contenido_litros,
            [(tipos.get(m, (None, False))[0], c) for m, c in p.materiales],
        )

    def _sku_libre(self, sku: str, excluir_id: int | None = None) -> None:
        if self._repo.existe_sku(sku, excluir_id):
            raise SkuDuplicado(f"Ya existe un producto con el SKU {sku}")  # RN-CAT-01


class CrearProducto(_Base):
    """Un TERMINADO se crea junto con su presentación, en la misma transacción."""

    def ejecutar(
        self, actor: Actor, datos: DatosProducto, presentacion: DatosPresentacion | None = None
    ) -> int:
        d = validar_producto(datos)
        self._validar_isc(d)
        self._validar_presentacion(d, presentacion)
        with self._atomic():
            unidad_id = self._unidad(d.unidad)
            self._sku_libre(d.sku)
            if d.activo:
                self._exigir_limite(actor.empresa_id)
            producto_id = self._repo.crear_producto(d, unidad_id)
            if d.tipo == TipoProducto.TERMINADO:
                self._repo.guardar_presentacion(producto_id, presentacion)
            return producto_id


class EditarProducto(_Base):
    """El estado se cambia con `CambiarEstadoProducto`, no aquí."""

    def ejecutar(
        self,
        actor: Actor,
        producto_id: int,
        datos: DatosProducto,
        presentacion: DatosPresentacion | None = None,
    ) -> None:
        original = self._repo.producto(producto_id)
        d = validar_producto(datos)
        d = replace(d, activo=original.activo)
        self._validar_isc(d)
        movimientos = self._puertos.inventario.tiene_movimientos(producto_id)
        if cambios_prohibidos(original, d, movimientos):
            raise CampoInmutable(INMUTABLE)
        if d.tipo == TipoProducto.TERMINADO:
            presentacion = presentacion or self._repo.presentacion(producto_id)
            self._validar_presentacion(d, presentacion)
            anterior = self._repo.presentacion(producto_id)
            if (
                movimientos
                and anterior
                and anterior.contenido_litros != presentacion.contenido_litros
            ):
                raise ContenidoInmutable(  # RF-CAT-18
                    "No se puede cambiar el contenido de una presentación con movimientos: "
                    "define el ISC de las unidades ya envasadas"
                )
        with self._atomic():
            self._sku_libre(d.sku, producto_id)
            self._repo.actualizar_producto(producto_id, d, self._unidad(d.unidad))
            if d.tipo == TipoProducto.TERMINADO:
                # Los materiales nuevos rigen para envasados futuros; el costo ya
                # congelado del stock existente no se toca (RF-CAT-18).
                self._repo.guardar_presentacion(producto_id, presentacion)


class CambiarEstadoProducto(_Base):
    """Desactivar no borra nada: el producto sigue en el historial (RF-CAT-19)."""

    def ejecutar(self, actor: Actor, producto_id: int, activo: bool) -> None:
        producto = self._repo.producto(producto_id)
        if activo == producto.activo:
            return
        if activo:
            self._exigir_limite(actor.empresa_id)
        else:
            motivo = puede_desactivar(
                self._puertos.inventario.stock(producto_id),
                producto.tipo == TipoProducto.GRANEL
                and self._repo.granel_con_presentaciones_activas(producto_id),
            )
            if motivo:
                raise NoSePuedeDesactivar(motivo)
        self._repo.cambiar_estado_producto(producto_id, activo)


class EliminarProducto(_Base):
    def ejecutar(self, actor: Actor, producto_id: int) -> None:
        self._repo.producto(producto_id)
        referencias = self._repo.referencias_internas(
            producto_id
        ) + self._puertos.referencias_externas(producto_id)
        movimientos = self._puertos.inventario.tiene_movimientos(producto_id)
        if not puede_eliminar(movimientos, referencias):
            raise NoSePuedeEliminar(CON_HISTORIAL)
        self._repo.eliminar_producto(producto_id)


class CrearFamilia(_Base):
    def ejecutar(self, actor: Actor, nombre: str) -> int:
        if not nombre.strip():
            raise UnidadInvalida("El nombre de la familia es obligatorio")
        return self._repo.crear_familia(nombre.strip())


# --- Unidades (UC-CAT-01) ---


class CrearUnidad(_Base):
    permiso_requerido = UNIDADES

    def ejecutar(self, actor: Actor, nombre: str, abreviatura: str, codigo_sunat: str) -> int:
        abreviatura = abreviatura.strip().upper()
        if not (nombre.strip() and abreviatura and codigo_sunat.strip()):
            raise UnidadInvalida("Nombre, abreviatura y código SUNAT son obligatorios")
        if self._repo.existe_unidad(abreviatura):
            raise UnidadInvalida(f"Ya existe la unidad {abreviatura}")
        return self._repo.crear_unidad(nombre.strip(), abreviatura, codigo_sunat.strip().upper())


class CambiarEstadoUnidad(_Base):
    permiso_requerido = UNIDADES

    def ejecutar(self, actor: Actor, unidad_id: int, activo: bool) -> None:
        if not activo and self._repo.unidad_en_uso(unidad_id, solo_activos=True):
            raise UnidadInvalida("La unidad la usan productos activos; no se puede desactivar")
        self._repo.cambiar_estado_unidad(unidad_id, activo)


class EliminarUnidad(_Base):
    permiso_requerido = UNIDADES

    def ejecutar(self, actor: Actor, unidad_id: int) -> None:
        if self._repo.unidad_en_uso(unidad_id, solo_activos=False):
            raise UnidadInvalida("La unidad está en uso; puedes desactivarla")  # RF-CAT-03
        self._repo.eliminar_unidad(unidad_id)
