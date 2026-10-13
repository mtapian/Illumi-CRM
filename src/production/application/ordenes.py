"""Casos de uso de la orden de producción (spec 0005a; plan §1 y §4)."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Protocol

from catalog.application.fachada import CatalogoQuery
from inventory.application.servicio import InventarioService, Linea
from production.domain.errores import OpInvalida
from production.domain.op import (
    SERVICIO,
    Componente,
    copiar_receta,
    costo_total,
    costo_unitario,
    excede,
    sugerir_lote,
    transicion,
    validar_componentes,
    validar_finalizacion,
    validar_stock,
)
from shared.application.autorizacion import Actor, CasoDeUso
from shared.application.puertos import SequencePort

PLANIFICAR = "produccion.op.planificar"
EJECUTAR = "produccion.op.ejecutar"
ANULAR = "produccion.op.anular"


@dataclass(frozen=True)
class DatosOp:
    producto_id: int
    cantidad: Decimal
    fecha_programada: date
    almacen_origen_id: int
    almacen_destino_id: int
    responsable_id: int | None = None  # por defecto, quien la crea (RF-PRD-35)
    comentario: str = ""  # p. ej. el pedido que atiende, sin vínculo (RF-PRD-36)
    componentes: tuple[Componente, ...] | None = None  # None al crear: según la receta


@dataclass(frozen=True)
class ConsumoReal:
    """Lo que realmente se consumió de un componente y de qué lote (None: según la estrategia
    del producto)."""

    producto_id: int
    consumido: Decimal
    lote: str | None = None


@dataclass(frozen=True)
class Finalizacion:
    producida: Decimal
    fecha_fin: date
    consumos: tuple[ConsumoReal, ...] = ()  # los que no vienen: lo por consumir
    costo_indirecto: Decimal = Decimal("0")
    lote: str = ""  # vacío: el sugerido (RF-PRD-46)
    vencimiento: date | None = None  # None: fecha de fin + vida útil
    motivo_perdida: str = ""


@dataclass(frozen=True)
class ComponenteFinal:
    producto_id: int
    consumido: Decimal
    lotes: str
    costo: Decimal


class OrdenesRepo(Protocol):
    def almacen_activo(self, almacen_id: int) -> bool | None: ...  # None: no existe
    def responsables(self) -> dict[int, str]: ...  # usuarios activos con EJECUTAR
    def crear(self, numero: int, datos: DatosOp, usuario_id: int) -> int: ...
    def actualizar(self, op_id: int, datos: DatosOp) -> None: ...
    def bloquear(self, op_id: int) -> tuple[str, DatosOp]: ...  # FOR UPDATE; 404 si no existe
    def en_proceso(self, op_id: int, usuario_id: int) -> None: ...
    def anular(self, op_id: int, usuario_id: int, motivo: str) -> None: ...
    def correlativo_lote(self, producto_id: int) -> int: ...  # lotes del producto + 1
    def finalizar(
        self,
        op_id: int,
        f: Finalizacion,
        componentes: list[ComponenteFinal],
        total: Decimal,
        unitario: Decimal | None,
        lote: str,
        usuario_id: int,
    ) -> None: ...


class _Base(CasoDeUso):
    permiso_requerido = PLANIFICAR

    def __init__(
        self,
        repo: OrdenesRepo,
        catalogo: CatalogoQuery,
        inventario: InventarioService,
        secuencia: SequencePort,
        atomic: Callable,
    ):
        self._repo, self._catalogo, self._inv = repo, catalogo, inventario
        self._secuencia, self._atomic = secuencia, atomic

    def _validar(self, actor: Actor, datos: DatosOp) -> DatosOp:
        """RF-PRD-35, 36, 38, 44; devuelve los datos normalizados."""
        p = self._catalogo.producto(datos.producto_id)
        if p is None or not (p.activo and p.tipo == "BIEN" and p.se_fabrica):
            raise OpInvalida("Elige un bien activo que se fabrique", "producto")
        if datos.cantidad <= 0:
            raise OpInvalida("La cantidad debe ser mayor a 0", "cantidad")
        for campo in ("almacen_origen_id", "almacen_destino_id"):
            activo = self._repo.almacen_activo(getattr(datos, campo))
            if not activo:
                mensaje = "Elige el almacén" if activo is None else "El almacén está desactivado"
                raise OpInvalida(mensaje, campo.removesuffix("_id"))
        responsable = datos.responsable_id or actor.usuario_id
        if responsable not in self._repo.responsables():
            raise OpInvalida(
                "El responsable debe ser un usuario activo que pueda ejecutar OP", "responsable"
            )
        componentes = tuple(datos.componentes or ())
        estados = {}
        for c in componentes:
            x = self._catalogo.producto(c.producto_id)
            if x is not None:
                estados[x.id] = (x.tipo, x.activo, x.sku)
        validar_componentes(datos.producto_id, componentes, estados)
        return replace(
            datos,
            responsable_id=responsable,
            comentario=datos.comentario.strip(),
            componentes=componentes,
        )


class CrearOp(_Base):
    """RF-PRD-36, 37: Creada, sin efecto en el stock; con la receta si se pide."""

    def ejecutar(self, actor: Actor, datos: DatosOp, usar_receta: bool = True) -> int:
        if datos.componentes is None:
            receta = self._catalogo.receta(datos.producto_id) if usar_receta else ()
            datos = replace(datos, componentes=copiar_receta(receta, datos.cantidad))
        datos = self._validar(actor, datos)
        with self._atomic():
            return self._repo.crear(self._secuencia.siguiente("OP"), datos, actor.usuario_id)


class EditarOp(_Base):
    """RF-PRD-38: mientras esté Creada o En proceso, sin mover stock; reemplaza la lista."""

    def ejecutar(self, actor: Actor, op_id: int, datos: DatosOp) -> None:
        with self._atomic():
            estado, actual = self._repo.bloquear(op_id)
            transicion(estado, "editar")
            if datos.componentes is None:
                datos = replace(datos, componentes=actual.componentes)
            self._repo.actualizar(op_id, self._validar(actor, datos))


class PasarAEnProceso(_Base):
    """RF-PRD-45: solo cambia el estado."""

    permiso_requerido = EJECUTAR

    def ejecutar(self, actor: Actor, op_id: int) -> None:
        with self._atomic():
            estado, _ = self._repo.bloquear(op_id)
            transicion(estado, "en_proceso")
            self._repo.en_proceso(op_id, actor.usuario_id)


class AnularOp(_Base):
    """RF-PRD-16, 18: Creada o En proceso, con motivo; no hay movimientos que revertir."""

    permiso_requerido = ANULAR

    def ejecutar(self, actor: Actor, op_id: int, motivo: str) -> None:
        if not motivo.strip():
            raise OpInvalida("Indica el motivo de la anulación", "motivo")
        with self._atomic():
            estado, _ = self._repo.bloquear(op_id)
            transicion(estado, "anular")
            self._repo.anular(op_id, actor.usuario_id, motivo.strip())


class FinalizarOp(_Base):
    """RF-PRD-41, 46, 09, 12, 14, 15, 47 (plan §4): en una transacción, con la OP bloqueada,
    consume los componentes al costo promedio e ingresa el producto con su lote. Devuelve las
    advertencias (rendimiento mayor a 100 %)."""

    permiso_requerido = EJECUTAR

    def ejecutar(self, actor: Actor, op_id: int, f: Finalizacion, hoy: date) -> list[str]:
        if f.costo_indirecto < 0:
            raise OpInvalida("El costo indirecto no puede ser negativo", "costo_indirecto")
        with self._atomic():
            estado, datos = self._repo.bloquear(op_id)  # la segunda espera y ve FINALIZADA
            transicion(estado, "finalizar")
            producto = self._catalogo.producto(datos.producto_id)
            if not (producto and producto.activo and producto.se_fabrica):
                raise OpInvalida("El producto ya no está activo o ya no se fabrica", "producto")
            validar_finalizacion(
                f.producida, f.motivo_perdida, len(datos.componentes), f.fecha_fin, hoy
            )
            reales = {c.producto_id: c for c in f.consumos}
            bienes, servicios, requeridos, disponibles = [], [], {}, {}
            for c in datos.componentes:
                real = reales.get(c.producto_id) or ConsumoReal(c.producto_id, c.por_consumir)
                x = self._catalogo.producto(c.producto_id)
                if x.tipo == SERVICIO:
                    servicios.append((real, c.costo_servicio or Decimal("0")))
                    continue
                bienes.append(real)
                if real.consumido > 0:
                    orden = self._inv.existencias_en_orden(
                        x.id, datos.almacen_origen_id, f.fecha_fin
                    )
                    requeridos[x.sku] = real.consumido
                    disponibles[x.sku] = sum(
                        (q for lote, q in orden if not real.lote or lote == real.lote), Decimal("0")
                    )
            validar_stock(requeridos, disponibles)  # RF-PRD-09: todos los faltantes
            lineas = [
                Linea(r.producto_id, datos.almacen_origen_id, r.consumido, lote=r.lote or None)
                for r in bienes
                if r.consumido > 0
            ]
            ids = (
                self._inv.registrar_salida(
                    "PRODUCCION", "OP", op_id, lineas, actor.usuario_id, f.fecha_fin
                )
                if lineas
                else []
            )
            importes, lotes = {}, {}
            for m in self._inv.consumido(ids):
                importes[m.producto_id] = importes.get(m.producto_id, Decimal("0")) + m.importe
                if m.lote:
                    lotes.setdefault(m.producto_id, set()).add(m.lote)
            total = costo_total(
                importes.values(), [costo for _, costo in servicios], f.costo_indirecto
            )
            unitario = costo_unitario(total, f.producida)
            lote = ""
            if f.producida > 0:
                lote = f.lote.strip() or sugerir_lote(
                    lotes, producto.sku, self._repo.correlativo_lote(producto.id)
                )
                self._inv.registrar_entrada(
                    "PRODUCCION",
                    "OP",
                    op_id,
                    [
                        Linea(
                            producto.id,
                            datos.almacen_destino_id,
                            f.producida,
                            unitario,
                            lote,
                            f.vencimiento,
                        )
                    ],
                    actor.usuario_id,
                    f.fecha_fin,
                )
            componentes = [
                ComponenteFinal(
                    r.producto_id,
                    r.consumido,
                    ", ".join(sorted(lotes.get(r.producto_id, ()))),
                    importes.get(r.producto_id, Decimal("0")),
                )
                for r in bienes
            ] + [ComponenteFinal(r.producto_id, r.consumido, "", costo) for r, costo in servicios]
            self._repo.finalizar(op_id, f, componentes, total, unitario, lote, actor.usuario_id)
        return ["Rendimiento mayor a 100 %"] if excede(datos.cantidad, f.producida) else []
