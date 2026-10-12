"""Unidades, categorías, marcas y productos (UC-CAT-01, 02, 04, 07 y 08; enmienda 4: bien o
servicio, casillas y receta)."""

from collections.abc import Callable
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Protocol

from catalog.application.puertos import Puertos
from catalog.domain.errores import (
    AgrupacionInvalida,
    CampoInmutable,
    CodigoBarrasDuplicado,
    ContenidoInmutable,
    IscInvalido,
    LimiteProductosPlan,
    NoSePuedeDesactivar,
    NoSePuedeEliminar,
    ProductoInvalido,
    RecetaInvalida,
    SkuDuplicado,
    UnidadInvalida,
)
from catalog.domain.producto import (
    DatosProducto,
    cabe_en_limite,
    cambios_prohibidos,
    instantanea,
    puede_desactivar,
    puede_eliminar,
    solo_cambios,
    validar_producto,
)
from catalog.domain.receta import CAMPO, Receta, hay_ciclo, validar_receta
from catalog.domain.tipos import TipoProducto
from shared.application.autorizacion import Actor, CasoDeUso

GESTIONAR = "catalogo.producto.gestionar"
ISC = "catalogo.isc.gestionar"
SIN_TASA = "Registra la tasa de ISC con su fecha de vigencia"
Tasa = tuple[Decimal, date]  # (monto por litro, vigente desde)
UNIDADES = "catalogo.unidad.gestionar"
AGRUPACIONES = ("categoria", "marca")  # RF-CAT-33, 34, 49
NOMBRE = {"categoria": "categoría", "marca": "marca"}  # para los mensajes
INMUTABLE = "No se puede modificar SKU, tipo o unidad de un producto con movimientos"
CON_HISTORIAL = "El producto tiene historial; solo puede desactivarse"
UNIDADES_INICIALES = [  # RF-CAT-01: (nombre, abreviatura, código SUNAT)
    ("Unidad", "UND", "NIU"),
    ("Kilogramo", "KG", "KGM"),
    ("Gramo", "G", "GRM"),
    ("Litro", "L", "LTR"),
    ("Mililitro", "ML", "MLT"),
    ("Caja", "CAJA", "BX"),  # enmienda 3
    ("Docena", "DOC", "DZN"),
    ("Metro", "MT", "MTR"),
    ("Paquete", "PAQ", "PK"),
    ("Servicio", "SERV", "ZZ"),
]


class CatalogoRepo(Protocol):
    """Todas las operaciones son de la empresa actual (TenantContext)."""

    def unidad_activa(self, abreviatura: str) -> int | None: ...
    def crear_unidad(self, nombre: str, abreviatura: str, codigo_sunat: str) -> int: ...
    def existe_unidad(self, abreviatura: str) -> bool: ...
    def unidad_en_uso(self, unidad_id: int, solo_activos: bool) -> bool: ...
    def cambiar_estado_unidad(self, unidad_id: int, activo: bool) -> None: ...
    def eliminar_unidad(self, unidad_id: int) -> None: ...
    def editar_unidad(self, unidad_id: int, nombre: str, abreviatura: str, codigo: str): ...
    def abreviatura_de(self, unidad_id: int) -> str: ...
    def existe_agrupacion(self, tipo: str, nombre: str, excluir_id: int | None = None) -> bool: ...
    def guardar_agrupacion(
        self, tipo: str, id_: int | None, nombre: str, descripcion: str, activo: bool | None
    ) -> int: ...
    def agrupacion_activa(self, tipo: str, id_: int) -> bool: ...
    def agrupacion_en_uso(self, tipo: str, id_: int) -> bool: ...
    def cambiar_estado_agrupacion(self, tipo: str, id_: int, activo: bool) -> None: ...
    def eliminar_agrupacion(self, tipo: str, id_: int) -> None: ...
    def existe_sku(self, sku: str, excluir_id: int | None = None) -> bool: ...
    def contar_activos(self) -> int: ...
    def producto(self, producto_id: int) -> DatosProducto: ...
    def crear_producto(self, datos: DatosProducto, unidad_id: int) -> int: ...
    def actualizar_producto(self, producto_id: int, datos: DatosProducto, unidad_id: int): ...
    def cambiar_estado_producto(self, producto_id: int, activo: bool) -> None: ...
    def eliminar_producto(self, producto_id: int) -> None: ...
    def referencias_internas(self, producto_id: int) -> int:
        """Recetas que lo usan como componente (RF-CAT-21, 41)."""
        ...

    def estados(self, ids) -> dict[int, tuple[TipoProducto, bool]]: ...
    def grafo_recetas(self) -> dict[int, set[int]]: ...
    def existe_tasa(self, producto_id: int, desde: date) -> bool: ...
    def agregar_tasa(self, producto_id: int, monto: Decimal, desde: date, actor_id: int): ...
    def tasas_isc(self, producto_id: int) -> list: ...
    def receta(self, producto_id: int) -> Receta: ...
    def guardar_receta(self, producto_id: int, receta: Receta) -> None: ...
    def sku_con_codigo_barras(self, codigo: str, excluir_id: int | None = None) -> str | None: ...
    def registrar_historial(
        self, producto_id: int, actor_id: int, accion: str, antes: dict | None, despues: dict | None
    ) -> None: ...


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
            raise UnidadInvalida(f"La unidad {abreviatura} no existe o está inactiva", "unidad")
        return unidad_id

    def _exigir_limite(self, empresa_id: int) -> None:
        # ponytail: sin lock; dos altas simultáneas en el último cupo podrían pasar ambas.
        # Pospuesto por el PO: spec 0002a, "Fuera de alcance".
        limite = self._limite(empresa_id)
        if not cabe_en_limite(self._repo.contar_activos(), limite):
            raise LimiteProductosPlan(f"Tu plan permite hasta {limite} productos activos")

    def _validar_agrupaciones(self, d: DatosProducto, original: DatosProducto | None) -> None:
        """
        Una categoría o marca inactiva no se asigna;
        quien ya la tiene la conserva (RF-CAT-33).
        """
        for tipo in AGRUPACIONES:
            id_ = getattr(d, f"{tipo}_id")
            cambia = original is None or getattr(original, f"{tipo}_id") != id_
            if id_ and cambia and not self._repo.agrupacion_activa(tipo, id_):
                raise ProductoInvalido(f"La {NOMBRE[tipo]} no existe o está inactiva", tipo)

    def _exigir_permiso_isc(self, actor: Actor, d, original, tasa) -> None:
        """Gestionar el ISC es de quien tiene `catalogo.isc.gestionar` (0001c; RF-CAT-45)."""
        campos = ("isc_sistema", "isc_codigo_tipo_sistema", "contenido_litros")
        cambia = original is None and d.afecto_isc
        cambia |= original is not None and any(
            getattr(d, c) != getattr(original, c) for c in campos
        )
        if cambia or tasa:
            actor.exige(ISC)

    def _agregar_tasa(self, actor: Actor, producto_id: int, tasa: Tasa) -> None:
        """Un cambio de tasa es una tasa nueva; las anteriores no se editan (RF-CAT-46)."""
        monto, desde = tasa
        if monto is None or monto <= 0:
            raise IscInvalido("La tasa de ISC por litro debe ser mayor a 0", "tasa_monto")
        if desde is None:
            raise IscInvalido("La fecha de vigencia de la tasa es obligatoria", "tasa_desde")
        if self._repo.existe_tasa(producto_id, desde):
            raise IscInvalido(
                f"Ya hay una tasa de ISC vigente desde {desde:%Y-%m-%d}", "tasa_desde"
            )
        self._repo.agregar_tasa(producto_id, monto, desde, actor.usuario_id)

    def _validar_receta(self, producto_id: int | None, receta: Receta) -> None:
        """Cualquier producto activo, sin repetidos, sin el propio producto ni ciclos."""
        validar_receta(producto_id, receta, self._repo.estados([c for c, _ in receta]))
        if producto_id and hay_ciclo(
            self._repo.grafo_recetas(), producto_id, {c for c, _ in receta}
        ):
            raise RecetaInvalida(
                "La receta crea un ciclo: un componente ya usa este producto", CAMPO
            )

    def _sku_libre(self, sku: str, excluir_id: int | None = None) -> None:
        if self._repo.existe_sku(sku, excluir_id):
            raise SkuDuplicado(f"Ya existe un producto con el SKU {sku}", "sku")  # RN-CAT-01

    def _codigo_barras_libre(self, codigo: str, excluir_id: int | None = None) -> None:
        if codigo and (sku := self._repo.sku_con_codigo_barras(codigo, excluir_id)):
            raise CodigoBarrasDuplicado(
                f"El código de barras ya está asignado a {sku}", "codigo_barras"
            )  # RF-CAT-31


class CrearProducto(_Base):
    """La receta es opcional y solo se guarda si el bien se fabrica (RF-CAT-41)."""

    def ejecutar(
        self,
        actor: Actor,
        datos: DatosProducto,
        receta: Receta | None = None,
        tasa: Tasa | None = None,
    ) -> int:
        d = validar_producto(datos)
        self._exigir_permiso_isc(actor, d, None, tasa)
        if d.afecto_isc and not tasa:
            raise IscInvalido(SIN_TASA, "tasa_monto")
        self._validar_agrupaciones(d, None)
        receta = tuple(receta or ()) if d.se_fabrica else ()
        self._validar_receta(None, receta)
        with self._atomic():
            unidad_id = self._unidad(d.unidad)
            self._sku_libre(d.sku)
            self._codigo_barras_libre(d.codigo_barras)
            if d.activo:
                self._exigir_limite(actor.empresa_id)
            producto_id = self._repo.crear_producto(d, unidad_id)
            if receta:
                self._repo.guardar_receta(producto_id, receta)
            if d.afecto_isc:
                self._agregar_tasa(actor, producto_id, tasa)
            self._repo.registrar_historial(producto_id, actor.usuario_id, "creado", None, None)
            return producto_id


class EditarProducto(_Base):
    """El estado se cambia con `CambiarEstadoProducto`, no aquí. `receta=None` no la toca:
    si se desmarca "se fabrica", la receta se conserva oculta (enmienda 4)."""

    def ejecutar(
        self,
        actor: Actor,
        producto_id: int,
        datos: DatosProducto,
        receta: Receta | None = None,
        tasa: Tasa | None = None,
    ) -> None:
        original = self._repo.producto(producto_id)
        d = replace(validar_producto(datos), activo=original.activo)
        self._exigir_permiso_isc(actor, d, original, tasa)
        if d.afecto_isc and not tasa and not self._repo.tasas_isc(producto_id):
            raise IscInvalido(SIN_TASA, "tasa_monto")
        self._validar_agrupaciones(d, original)
        movimientos = self._puertos.inventario.tiene_movimientos(producto_id)
        if prohibidos := cambios_prohibidos(original, d, movimientos):
            raise CampoInmutable(INMUTABLE, prohibidos[0])
        if (
            movimientos
            and original.contenido_litros
            and (d.contenido_litros != original.contenido_litros)
        ):
            raise ContenidoInmutable(  # RF-CAT-46 (antes RF-CAT-18)
                "No se puede cambiar el contenido en litros de un producto con movimientos: "
                "define el ISC de las unidades ya producidas o compradas",
                "contenido_litros",
            )
        previa = self._repo.receta(producto_id)
        if receta is not None and d.se_fabrica:
            receta = tuple(receta)
            self._validar_receta(producto_id, receta)
        else:
            receta = None
        with self._atomic():
            self._sku_libre(d.sku, producto_id)
            self._codigo_barras_libre(d.codigo_barras, producto_id)
            self._repo.actualizar_producto(producto_id, d, self._unidad(d.unidad))
            if receta is not None:
                # Rige para producciones futuras; el costo ya congelado no cambia (RF-CAT-18).
                self._repo.guardar_receta(producto_id, receta)
            if tasa and d.afecto_isc:
                self._agregar_tasa(actor, producto_id, tasa)
            antes, despues = solo_cambios(
                instantanea(original, previa), instantanea(d, previa if receta is None else receta)
            )
            if despues:
                self._repo.registrar_historial(
                    producto_id, actor.usuario_id, "editado", antes, despues
                )


class AgregarTasaIsc(_Base):
    """Tasa nueva con su vigencia para un producto afecto a ISC (RF-CAT-46)."""

    permiso_requerido = ISC

    def ejecutar(self, actor: Actor, producto_id: int, monto: Decimal, desde: date) -> None:
        if not self._repo.producto(producto_id).afecto_isc:
            raise IscInvalido("El producto no está afecto a ISC")
        with self._atomic():
            self._agregar_tasa(actor, producto_id, (monto, desde))


class CambiarEstadoProducto(_Base):
    """Desactivar no borra nada: el producto sigue en el historial (RF-CAT-19)."""

    def ejecutar(self, actor: Actor, producto_id: int, activo: bool) -> None:
        producto = self._repo.producto(producto_id)
        if activo == producto.activo:
            return
        if activo:
            self._exigir_limite(actor.empresa_id)
        else:
            motivo = puede_desactivar(self._puertos.inventario.stock(producto_id))
            if motivo:
                raise NoSePuedeDesactivar(motivo)
        with self._atomic():
            self._repo.cambiar_estado_producto(producto_id, activo)
            self._repo.registrar_historial(
                producto_id,
                actor.usuario_id,
                "activado" if activo else "desactivado",
                {"activo": not activo},
                {"activo": activo},
            )


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


# --- Categorías y marcas (UC-CAT-07) ---


class _Agrupacion(_Base):
    def _tipo(self, tipo: str) -> str:
        if tipo not in AGRUPACIONES:
            raise AgrupacionInvalida(f"Agrupación desconocida: {tipo}")
        return tipo


class GuardarAgrupacion(_Agrupacion):
    """Crea (`id_=None`) o edita una categoría o marca (RF-CAT-33, 34, 50). La descripción
    solo la tienen las categorías; `activo=None` no cambia el estado."""

    def ejecutar(
        self,
        actor: Actor,
        tipo: str,
        id_: int | None,
        nombre: str,
        descripcion: str = "",
        activo: bool | None = None,
    ) -> int:
        tipo, nombre = self._tipo(tipo), nombre.strip()
        if not nombre:
            raise AgrupacionInvalida(f"El nombre de la {NOMBRE[tipo]} es obligatorio", "nombre")
        if self._repo.existe_agrupacion(tipo, nombre, id_):
            raise AgrupacionInvalida(f"Ya existe la {NOMBRE[tipo]} {nombre}", "nombre")
        return self._repo.guardar_agrupacion(tipo, id_, nombre, descripcion.strip(), activo)


class CambiarEstadoAgrupacion(_Agrupacion):
    def ejecutar(self, actor: Actor, tipo: str, id_: int, activo: bool) -> None:
        self._repo.cambiar_estado_agrupacion(self._tipo(tipo), id_, activo)


class EliminarAgrupacion(_Agrupacion):
    def ejecutar(self, actor: Actor, tipo: str, id_: int) -> None:
        if self._repo.agrupacion_en_uso(self._tipo(tipo), id_):
            raise AgrupacionInvalida(f"La {NOMBRE[tipo]} está en uso; puedes desactivarla")
        self._repo.eliminar_agrupacion(tipo, id_)


# --- Unidades (UC-CAT-01) ---


def _obligatorios_unidad(nombre: str, abreviatura: str, codigo_sunat: str) -> None:
    for campo, valor in (
        ("nombre", nombre),
        ("abreviatura", abreviatura),
        ("codigo_sunat", codigo_sunat),
    ):
        if not valor.strip():
            raise UnidadInvalida("Nombre, abreviatura y código SUNAT son obligatorios", campo)


class CrearUnidad(_Base):
    permiso_requerido = UNIDADES

    def ejecutar(self, actor: Actor, nombre: str, abreviatura: str, codigo_sunat: str) -> int:
        abreviatura = abreviatura.strip().upper()
        _obligatorios_unidad(nombre, abreviatura, codigo_sunat)
        if self._repo.existe_unidad(abreviatura):
            raise UnidadInvalida(f"Ya existe la unidad {abreviatura}", "abreviatura")
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


class EditarUnidad(_Base):
    """Nombre y código SUNAT siempre; la abreviatura solo si nadie la usa (RF-CAT-35)."""

    permiso_requerido = UNIDADES

    def ejecutar(
        self, actor: Actor, unidad_id: int, nombre: str, abreviatura: str, codigo_sunat: str
    ) -> None:
        abreviatura = abreviatura.strip().upper()
        _obligatorios_unidad(nombre, abreviatura, codigo_sunat)
        if abreviatura != self._repo.abreviatura_de(unidad_id):
            if self._repo.unidad_en_uso(unidad_id, solo_activos=False):
                raise UnidadInvalida(
                    "La unidad está en uso: su abreviatura no se puede cambiar", "abreviatura"
                )
            if self._repo.existe_unidad(abreviatura):
                raise UnidadInvalida(f"Ya existe la unidad {abreviatura}", "abreviatura")
        self._repo.editar_unidad(
            unidad_id, nombre.strip(), abreviatura, codigo_sunat.strip().upper()
        )
