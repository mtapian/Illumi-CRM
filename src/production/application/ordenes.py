"""Casos de uso de la orden de producción (spec 0005a; plan §1 y §4; enmienda 1: varias salidas)."""

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
    Salida,
    copiar_receta,
    costo_total,
    costo_unitario,
    excede,
    repartir,
    sugerir_lote,
    transicion,
    validar_componentes,
    validar_finalizacion,
    validar_salidas,
    validar_stock,
)
from shared.application.autorizacion import Actor, CasoDeUso
from shared.application.puertos import SequencePort

PLANIFICAR = "produccion.op.planificar"
EJECUTAR = "produccion.op.ejecutar"
ANULAR = "produccion.op.anular"
CERO = Decimal("0")


@dataclass(frozen=True)
class DatosOp:
    salidas: tuple[Salida, ...]  # productos de salida (enmienda 1, RF-PRD-49)
    fecha_programada: date
    almacen_origen_id: int
    almacen_destino_id: int
    responsable_id: int | None = None  # por defecto, quien la crea (RF-PRD-35)
    comentario: str = ""  # p. ej. el pedido que atiende, sin vínculo (RF-PRD-36)
    componentes: tuple[Componente, ...] | None = None  # None al crear: según las recetas


@dataclass(frozen=True)
class ConsumoReal:
    """Lo que realmente se consumió de un componente (de una salida o común) y de qué lote
    (None: según la estrategia del producto)."""

    producto_id: int
    consumido: Decimal
    lote: str | None = None
    salida: int | None = None


@dataclass(frozen=True)
class Producido:
    """Lo producido de una salida y su lote (vacío: el sugerido; RF-PRD-46, 52)."""

    producto_id: int
    cantidad: Decimal
    lote: str = ""
    vencimiento: date | None = None  # None: fecha de fin + vida útil


@dataclass(frozen=True)
class Finalizacion:
    producidos: tuple[Producido, ...]  # las salidas que no vienen: lo programado
    fecha_fin: date
    consumos: tuple[ConsumoReal, ...] = ()  # los que no vienen: lo por consumir
    costo_indirecto: Decimal = CERO
    motivo_perdida: str = ""


@dataclass(frozen=True)
class ComponenteFinal:
    producto_id: int
    salida: int | None
    consumido: Decimal
    lotes: str
    costo: Decimal


@dataclass(frozen=True)
class SalidaFinal:
    producto_id: int
    producida: Decimal
    lote: str
    costo: Decimal
    unitario: Decimal | None


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
        salidas: list[SalidaFinal],
        total: Decimal,
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

    def _fabricable(self, producto_id: int) -> bool:
        p = self._catalogo.producto(producto_id)
        return bool(p and p.activo and p.tipo == "BIEN" and p.se_fabrica)

    def _validar(self, actor: Actor, datos: DatosOp) -> DatosOp:
        """RF-PRD-35, 36, 38, 44, 49, 51; devuelve los datos normalizados."""
        validar_salidas(datos.salidas)
        if not all(self._fabricable(x.producto_id) for x in datos.salidas):
            raise OpInvalida("Elige un bien activo que se fabrique", "salidas")
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
        validar_componentes({x.producto_id for x in datos.salidas}, componentes, estados)
        return replace(
            datos,
            responsable_id=responsable,
            comentario=datos.comentario.strip(),
            componentes=componentes,
        )


class CrearOp(_Base):
    """RF-PRD-36, 37, 50: Creada, sin efecto en el stock; con la receta de cada salida si se
    pide, asignada a ella."""

    def ejecutar(self, actor: Actor, datos: DatosOp, usar_receta: bool = True) -> int:
        if datos.componentes is None:
            componentes = ()
            if usar_receta:
                for x in datos.salidas:
                    receta = self._catalogo.receta(x.producto_id)
                    componentes += copiar_receta(receta, x.cantidad, x.producto_id)
            datos = replace(datos, componentes=componentes)
        datos = self._validar(actor, datos)
        with self._atomic():
            return self._repo.crear(self._secuencia.siguiente("OP"), datos, actor.usuario_id)


class EditarOp(_Base):
    """RF-PRD-38, 49: mientras esté Creada o En proceso, sin mover stock; reemplaza salidas y
    componentes (una OP de un producto puede pasar a varios)."""

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
    """RF-PRD-41, 46, 09, 12, 14, 15, 47, 52 (plan §4 y enmienda 1): en una transacción, con
    la OP bloqueada, consume los componentes al costo promedio, reparte el costo entre las
    salidas e ingresa cada una con su lote. Devuelve las advertencias."""

    permiso_requerido = EJECUTAR

    def ejecutar(self, actor: Actor, op_id: int, f: Finalizacion, hoy: date) -> list[str]:
        if f.costo_indirecto < 0:
            raise OpInvalida("El costo indirecto no puede ser negativo", "costo_indirecto")
        with self._atomic():
            estado, datos = self._repo.bloquear(op_id)  # la segunda espera y ve FINALIZADA
            transicion(estado, "finalizar")
            if not all(self._fabricable(x.producto_id) for x in datos.salidas):
                raise OpInvalida("El producto ya no está activo o ya no se fabrica", "salidas")
            pedidos = {p.producto_id: p for p in f.producidos}
            producidos = [
                pedidos.get(x.producto_id) or Producido(x.producto_id, x.cantidad)
                for x in datos.salidas
            ]
            if any(p.cantidad < 0 for p in producidos):
                raise OpInvalida("La cantidad producida no puede ser negativa", "producida")
            total_producido = sum((p.cantidad for p in producidos), CERO)
            validar_finalizacion(total_producido, f.motivo_perdida, f.fecha_fin, hoy)

            reales = {(c.producto_id, c.salida): c for c in f.consumos}
            filas = []  # (componente, real, es servicio, sku)
            requeridos, disponibles = {}, {}
            for c in datos.componentes:
                real = reales.get((c.producto_id, c.salida)) or ConsumoReal(
                    c.producto_id, c.por_consumir, salida=c.salida
                )
                x = self._catalogo.producto(c.producto_id)
                filas.append((c, real, x.tipo == SERVICIO, x.sku))
                if x.tipo == SERVICIO or real.consumido <= 0:
                    continue
                clave = f"{x.sku} ({real.lote})" if real.lote else x.sku
                requeridos[clave] = requeridos.get(clave, CERO) + real.consumido
                if clave not in disponibles:
                    orden = self._inv.existencias_en_orden(
                        x.id, datos.almacen_origen_id, f.fecha_fin
                    )
                    disponibles[clave] = sum(
                        (q for lote, q in orden if not real.lote or lote == real.lote), CERO
                    )
            validar_stock(requeridos, disponibles)  # RF-PRD-09: todos los faltantes

            finales, directos, comunes, lotes = [], {}, CERO, {}
            for c, real, servicio, _ in filas:
                importe, usados = c.costo_servicio or CERO, set()
                if not servicio and real.consumido > 0:
                    linea = Linea(
                        c.producto_id, datos.almacen_origen_id, real.consumido, lote=real.lote
                    )
                    ids = self._inv.registrar_salida(
                        "PRODUCCION", "OP", op_id, [linea], actor.usuario_id, f.fecha_fin
                    )
                    consumos = self._inv.consumido(ids)
                    importe = sum((m.importe for m in consumos), CERO)
                    usados = {m.lote for m in consumos if m.lote}
                if c.salida is None:
                    comunes += importe
                else:
                    directos[c.salida] = directos.get(c.salida, CERO) + importe
                if usados:
                    lotes.setdefault(c.salida, {})[c.producto_id] = usados
                finales.append(
                    ComponenteFinal(
                        c.producto_id, c.salida, real.consumido, ", ".join(sorted(usados)), importe
                    )
                )

            factores = {x.producto_id: x.factor for x in datos.salidas}
            costos = repartir(
                [(p.producto_id, p.cantidad, factores[p.producto_id]) for p in producidos],
                directos,
                comunes,
                f.costo_indirecto,
            )
            total = costo_total([*directos.values(), comunes], [], f.costo_indirecto)
            salidas = []
            for p in producidos:
                unitario, lote = costo_unitario(costos[p.producto_id], p.cantidad), ""
                if p.cantidad > 0:
                    producto = self._catalogo.producto(p.producto_id)
                    propios = lotes.get(p.producto_id) or lotes.get(None, {})
                    lote = p.lote.strip() or sugerir_lote(
                        propios, producto.sku, self._repo.correlativo_lote(p.producto_id)
                    )
                    entrada = Linea(
                        p.producto_id,
                        datos.almacen_destino_id,
                        p.cantidad,
                        unitario,
                        lote,
                        p.vencimiento,
                    )
                    self._inv.registrar_entrada(
                        "PRODUCCION", "OP", op_id, [entrada], actor.usuario_id, f.fecha_fin
                    )
                salidas.append(
                    SalidaFinal(p.producto_id, p.cantidad, lote, costos[p.producto_id], unitario)
                )
            self._repo.finalizar(op_id, f, finales, salidas, total, actor.usuario_id)
        programadas = {x.producto_id: x.cantidad for x in datos.salidas}
        if any(excede(programadas[p.producto_id], p.cantidad) for p in producidos):
            return ["Rendimiento mayor a 100 %"]
        return []
