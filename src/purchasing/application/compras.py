"""Registro de compras (UC-COM-02, spec 0004a): Creada ▸ En proceso ▸ Finalizada.

Crear y editar validan y no mueven stock (RF-COM-25); finalizar vuelve a validar y registra
la entrada de inventario en la misma transacción (RF-COM-26, 27).
"""

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal
from typing import Protocol

from catalog.application.fachada import CatalogoQuery
from inventory.application.servicio import AnulacionConConsumoPosterior, InventarioService, Linea
from purchasing.application.puertos import IgvPort
from purchasing.domain.compra import (
    ANULADA,
    CREADA,
    DOCUMENTOS,
    EN_PROCESO,
    FINALIZADA,
    SIN_DOCUMENTO,
    LineaCompra,
    numero_compra,
    totales,
    validar_documento_compra,
    validar_guia,
    validar_linea,
)
from purchasing.domain.errores import CompraInvalida
from shared.application.autorizacion import Actor, CasoDeUso
from shared.application.puertos import SequencePort
from shared.domain.errores import DomainError, NoEncontrado

VER, REGISTRAR, ANULAR = "compras.compra.ver", "compras.compra.registrar", "compras.compra.anular"
REF = "COMPRA"
NO_COMPRABLE = "Solo se pueden comprar bienes activos que se compran"


@dataclass(frozen=True)
class DatosCompra:
    proveedor_id: int | None
    fecha: date
    almacen_id: int | None
    doc_tipo: str
    doc_serie_numero: str
    observacion: str = ""
    lineas: list[LineaCompra] = field(default_factory=list)


@dataclass(frozen=True)
class Totales:
    igv_pct: Decimal
    subtotal: Decimal
    igv: Decimal
    total: Decimal


class ComprasRepo(Protocol):
    def proveedor(self, proveedor_id: int) -> tuple[bool, str, str] | None: ...  # activo, doc
    def almacen_activo(self, almacen_id: int) -> bool | None: ...  # None: no existe
    def con_documento(self, proveedor_id, doc_tipo, serie, excluir) -> int | None: ...  # número
    def crear(self, numero: int, datos: DatosCompra, t: Totales, usuario_id) -> int: ...
    def actualizar(self, compra_id: int, datos: DatosCompra, t: Totales) -> None: ...
    def bloquear(self, compra_id: int) -> tuple[str, DatosCompra] | None: ...  # FOR UPDATE
    def cambiar_estado(self, compra_id: int, estado: str) -> None: ...
    def finalizar(self, compra_id, almacen_id, recepcion, guia, usuario_id) -> None: ...
    def anular(self, compra_id: int, usuario_id, motivo: str) -> None: ...


class _Base(CasoDeUso):
    permiso_requerido = REGISTRAR

    def __init__(
        self,
        repo: ComprasRepo,
        catalogo: CatalogoQuery,
        igv: IgvPort,
        secuencia: SequencePort,
        inventario: InventarioService,
        atomic: Callable,
    ):
        self._repo, self._catalogo, self._igv = repo, catalogo, igv
        self._secuencia, self._inv, self._atomic = secuencia, inventario, atomic

    def _almacen(self, almacen_id: int | None) -> None:
        activo = self._repo.almacen_activo(almacen_id) if almacen_id else None
        if activo is None:
            raise CompraInvalida("Elige el almacén", "almacen")
        if not activo:
            raise CompraInvalida("El almacén está desactivado", "almacen")

    def _validar(self, datos: DatosCompra, excluir: int | None = None) -> DatosCompra:
        """RF-COM-04, 05, 11, 20 y 23; devuelve los datos normalizados."""
        proveedor = self._repo.proveedor(datos.proveedor_id) if datos.proveedor_id else None
        if proveedor is None:
            raise CompraInvalida("Elige un proveedor", "proveedor")
        activo, tipo_doc, razon_social = proveedor
        if not activo:
            raise CompraInvalida("El proveedor está desactivado", "proveedor")
        serie = validar_documento_compra(datos.doc_tipo, datos.doc_serie_numero, tipo_doc)
        self._almacen(datos.almacen_id)
        if not datos.lineas:
            raise CompraInvalida("La compra debe tener al menos una línea", "lineas")
        for x in datos.lineas:
            validar_linea(x.cantidad, x.costo_unitario, x.bonificacion)
            p = self._catalogo.producto(x.producto_id)
            if p is None or not (p.activo and p.tipo == "BIEN" and p.se_compra):
                raise CompraInvalida(NO_COMPRABLE, "lineas")
        if datos.doc_tipo != SIN_DOCUMENTO:
            n = self._repo.con_documento(datos.proveedor_id, datos.doc_tipo, serie, excluir)
            if n is not None:
                raise CompraInvalida(
                    f"La {DOCUMENTOS[datos.doc_tipo]} {serie} de {razon_social} ya fue "
                    f"registrada en {numero_compra(n)}",
                    "doc_serie_numero",
                )
        return replace(datos, doc_serie_numero=serie, observacion=datos.observacion.strip())

    def _totales(self, datos: DatosCompra) -> Totales:
        """RF-COM-08 y 09 (ajustado por RF-CAT-61): el IGV de cada línea sale del impuesto de
        compra de su producto a la fecha de la compra. `igv_pct` guarda el mayor % usado."""
        empresa = self._igv.igv_vigente(datos.fecha)
        # Un producto sin impuesto de compra (la conversión de 0002e los asignó a todos) toma
        # el IGV de la empresa.
        tasas = [
            self._catalogo.igv_de_compra(x.producto_id, datos.fecha) or ("PORCENTAJE", empresa)
            for x in datos.lineas
        ]
        pct = max((i for c, i in tasas if c == "PORCENTAJE"), default=Decimal("0"))
        return Totales(pct, *totales(datos.lineas, datos.doc_tipo, tasas))

    def _editable(self, compra_id: int) -> tuple[str, DatosCompra]:
        fila = self._repo.bloquear(compra_id)
        if fila is None:
            raise NoEncontrado("La compra no existe")
        if fila[0] == FINALIZADA:  # RF-COM-13
            raise CompraInvalida("La compra ya está finalizada")
        if fila[0] == ANULADA:
            raise CompraInvalida("La compra está anulada")
        return fila


class CrearCompra(_Base):
    """RF-COM-04: queda Creada, con su número, sin mover stock."""

    def ejecutar(self, actor: Actor, datos: DatosCompra) -> int:
        datos = self._validar(datos)
        with self._atomic():
            numero = self._secuencia.siguiente(REF)
            return self._repo.crear(numero, datos, self._totales(datos), actor.usuario_id)


class EditarCompra(_Base):
    """RF-COM-25: cabecera y líneas mientras no esté Finalizada; sin stock."""

    def ejecutar(self, actor: Actor, compra_id: int, datos: DatosCompra) -> None:
        with self._atomic():
            self._editable(compra_id)
            datos = self._validar(datos, excluir=compra_id)
            self._repo.actualizar(compra_id, datos, self._totales(datos))


class PasarAEnProceso(_Base):
    """RF-COM-25: de Creada a En proceso; no vuelve atrás."""

    def ejecutar(self, actor: Actor, compra_id: int) -> None:
        with self._atomic():
            estado, _ = self._editable(compra_id)
            if estado != CREADA:
                raise CompraInvalida("La compra ya está en proceso")
            self._repo.cambiar_estado(compra_id, EN_PROCESO)


class FinalizarCompra(_Base):
    """RF-COM-26 y 27: confirma la recepción (almacén, fecha y guía), revalida la compra y
    registra una entrada por línea al costo indicado (RF-COM-10)."""

    def ejecutar(
        self,
        actor: Actor,
        compra_id: int,
        almacen_id: int | None,
        recepcion: date,
        guia: str,
        hoy: date,
    ) -> None:
        if recepcion > hoy:
            raise CompraInvalida("La fecha de recepción no puede ser futura", "fecha_recepcion")
        guia = validar_guia(guia)
        with self._atomic():
            estado, datos = self._editable(compra_id)
            if estado == CREADA:  # RF-COM-30: sin saltos
                raise CompraInvalida("Pasa la compra a en proceso antes de finalizarla")
            datos = self._validar(replace(datos, almacen_id=almacen_id), excluir=compra_id)
            self._repo.finalizar(compra_id, almacen_id, recepcion, guia, actor.usuario_id)
            lineas = [
                Linea(
                    x.producto_id, almacen_id, x.cantidad, x.costo_unitario, x.lote, x.vencimiento
                )
                for x in datos.lineas
            ]
            try:
                usuario = actor.usuario_id
                self._inv.registrar_entrada(REF, REF, compra_id, lineas, usuario, recepcion)
            except DomainError as e:  # lote con otro vencimiento, etc.: el error es de las líneas
                e.campo = e.campo or "lineas"
                raise


class AnularCompra(_Base):
    """RF-COM-15 a 18, 28 y 29 (spec 0004b): una Finalizada revierte sus entradas al mismo
    costo; una Creada o En proceso solo cambia de estado. Una sola vez."""

    permiso_requerido = ANULAR

    def ejecutar(self, actor: Actor, compra_id: int, motivo: str) -> None:
        motivo = motivo.strip()
        if not motivo:
            raise CompraInvalida("El motivo es obligatorio", "motivo")
        with self._atomic():
            fila = self._repo.bloquear(compra_id)  # el segundo espera y ve ANULADA (RF-COM-17)
            if fila is None:
                raise NoEncontrado("La compra no existe")
            if fila[0] == ANULADA:
                raise CompraInvalida("La compra ya está anulada")
            if fila[0] == FINALIZADA:
                try:
                    self._inv.revertir(REF, compra_id, actor.usuario_id)
                except AnulacionConConsumoPosterior as e:
                    producto = self._catalogo.producto(e.producto_id)
                    sku = producto.sku if producto else "un producto"
                    raise CompraInvalida(
                        f"No se puede anular: {sku} tuvo salidas posteriores a la compra. "
                        "Corrígela con un ajuste CORRECCION"
                    ) from None
            self._repo.anular(compra_id, actor.usuario_id, motivo)
