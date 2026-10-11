"""Servicio de inventario (plan 0003a §1 y §4): la única puerta para cambiar stock.

Compras, producción y ventas lo llaman dentro de la transacción de su caso de uso, que ya
verificó el permiso; por eso no es un `CasoDeUso`. Orden de locks (plan 0000 §5):
`costo_producto` de los productos involucrados, por `producto_id`, y después su stock.
"""

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Protocol

from catalog.application.fachada import CatalogoQuery, ProductoDTO
from inventory.domain import costo as cp
from inventory.domain.errores import CostoRequerido
from inventory.domain.existencia import ENTRADA, SALIDA, Existencia, Movimiento, salir
from inventory.domain.fefo import asignar_fefo
from inventory.domain.lotes import (
    sugerir_vencimiento,
    validar_bien,
    validar_lote_existente,
    validar_salida_de_lote,
)
from inventory.domain.movimientos import inversos_de, validar_reversion
from shared.domain.errores import NoEncontrado

COSTO_REQUERIDO = "El costo unitario es obligatorio en una entrada"
ANULACION = "ANULACION"
TRANSFERENCIA = "TRANSFERENCIA"


@dataclass(frozen=True)
class Linea:
    producto_id: int
    almacen_id: int
    cantidad: Decimal
    costo_unitario: Decimal | None = None  # obligatorio en entradas
    lote: str | None = None  # código; en salidas, None = FEFO
    vencimiento: date | None = None  # solo en entradas con lote
    exacto: bool = False  # en salidas: `lote=None` es el stock sin lote, no FEFO (CONTEO)


class InventarioRepo(Protocol):
    def bloquear(self, producto_ids: list[int]) -> None: ...
    def costo(self, producto_id: int) -> cp.CostoProducto: ...
    def guardar_costo(self, producto_id: int, costo: cp.CostoProducto) -> None: ...
    def almacen(self, almacen_id: int) -> str | None: ...
    def existencias(self, producto_id: int, almacen_id: int) -> list[Existencia]: ...
    def lote(self, producto_id: int, codigo: str) -> tuple[int, date | None] | None: ...
    def crear_lote(self, producto_id, codigo, ingreso, vencimiento, origen) -> int: ...
    def sumar_stock(self, producto_id, almacen_id, lote_id, cantidad: Decimal) -> None: ...
    def fijar_stock(self, stock_id: int, cantidad: Decimal) -> None: ...
    def insertar_movimiento(self, **campos) -> int: ...
    def por_revertir(self, ref_tipo: str, ref_id: int) -> list[Movimiento]: ...
    def movimientos(self, producto_id: int) -> list[Movimiento]: ...


class InventarioService:
    def __init__(self, repo: InventarioRepo, catalogo: CatalogoQuery):
        self._repo, self._catalogo = repo, catalogo

    def bloquear(self, producto_ids: list[int]) -> None:
        """Para casos de uso que llaman varias veces al inventario: bloquear antes de la
        primera llamada (plan 0000 §5)."""
        self._repo.bloquear(sorted(set(producto_ids)))

    def _producto(self, producto_id: int) -> ProductoDTO:
        producto = self._catalogo.producto(producto_id)
        if producto is None:
            raise NoEncontrado("El producto no existe")
        validar_bien(producto.tipo)  # RF-INV-25
        return producto

    def _almacen(self, almacen_id: int) -> str:
        nombre = self._repo.almacen(almacen_id)
        if nombre is None:
            raise NoEncontrado("El almacén no existe")
        return nombre

    def _registrar(self, ref, usuario_id, despues: cp.CostoProducto, monto, **mov) -> int:
        """RF-INV-17: exactamente un movimiento por cambio de stock, con costo y saldo."""
        self._repo.guardar_costo(mov["producto_id"], despues)
        return self._repo.insertar_movimiento(
            **mov
            | {
                "cantidad": cp.cantidad(mov["cantidad"]),
                "costo_unitario": cp.costo_unitario(mov["costo_unitario"]),
                "costo_total": monto,
                "saldo_cantidad": despues.cantidad,
                "saldo_promedio": despues.promedio,
                "ref_tipo": ref[0],
                "ref_id": ref[1],
                "usuario_id": usuario_id,
            }
        )

    def registrar_entrada(
        self, motivo, ref_tipo, ref_id, lineas: list[Linea], usuario_id, hoy: date
    ) -> list[int]:
        """RF-INV-17, 18 y 26."""
        self.bloquear([x.producto_id for x in lineas])
        ids = []
        for x in lineas:
            producto = self._producto(x.producto_id)
            self._almacen(x.almacen_id)
            if x.costo_unitario is None:
                raise CostoRequerido(COSTO_REQUERIDO)
            lote_id = None
            if x.lote:
                existente = self._repo.lote(x.producto_id, x.lote)
                if existente:
                    lote_id, vence = existente
                    validar_lote_existente(x.lote, vence, x.vencimiento)
                else:
                    vence = x.vencimiento or sugerir_vencimiento(hoy, producto.vida_util_dias)
                    lote_id = self._repo.crear_lote(
                        x.producto_id, x.lote, hoy, vence, (ref_tipo, ref_id)
                    )
            antes = self._repo.costo(x.producto_id)
            despues = cp.entrada(antes, x.cantidad, x.costo_unitario)
            self._repo.sumar_stock(x.producto_id, x.almacen_id, lote_id, cp.cantidad(x.cantidad))
            monto = despues.valor - antes.valor
            ids.append(
                self._registrar(
                    (ref_tipo, ref_id),
                    usuario_id,
                    despues,
                    monto,
                    tipo=ENTRADA,
                    motivo=motivo,
                    producto_id=x.producto_id,
                    almacen_id=x.almacen_id,
                    lote_id=lote_id,
                    cantidad=x.cantidad,
                    costo_unitario=x.costo_unitario,
                )
            )
        return ids

    def _existencias(self, x: Linea, producto: ProductoDTO, almacen: str) -> list[Existencia]:
        return [
            replace(e, producto=producto.sku, almacen=almacen)
            for e in self._repo.existencias(x.producto_id, x.almacen_id)
        ]

    def _asignar(
        self, x: Linea, producto, almacen, motivo, hoy
    ) -> list[tuple[Existencia, Decimal]]:
        """De qué existencias sale `x`: el lote indicado (o el stock sin lote si `exacto`); si
        no, FEFO cuando hay stock con lote; si no, el stock sin lote (RF-INV-22, 23)."""
        existencias = self._existencias(x, producto, almacen)
        vacia = Existencia(Decimal("0"), x.lote, producto=producto.sku, almacen=almacen)
        if x.lote or x.exacto:
            e = next((e for e in existencias if e.lote == x.lote), vacia)
            validar_salida_de_lote(e, motivo, hoy)
            return [(e, x.cantidad)]
        if any(e.lote for e in existencias):
            return asignar_fefo(existencias, x.cantidad, hoy, producto.unidad)
        return [(existencias[0] if existencias else vacia, x.cantidad)]

    def stock_en(self, producto_id: int, almacen_id: int, lote: str | None) -> Decimal:
        """Stock de una existencia (lote `None` = sin lote), para el CONTEO de 0003b."""
        self._almacen(almacen_id)
        existencias = self._repo.existencias(producto_id, almacen_id)
        return next((e.cantidad for e in existencias if e.lote == lote), Decimal("0"))

    def promedio_vigente(self, producto_id: int) -> Decimal | None:
        """None si el producto nunca tuvo movimientos (RF-INV-27)."""
        if not self._repo.movimientos(producto_id):
            return None
        return self._repo.costo(producto_id).promedio

    def tiene_movimientos(self, producto_id: int) -> bool:
        return bool(self._repo.movimientos(producto_id))

    def transferir(
        self, ref_tipo, ref_id, lineas: list[Linea], destino_id: int, usuario_id, hoy: date
    ) -> list[int]:
        """RF-INV-12: salida del origen y entrada al destino en el mismo lote, al promedio
        vigente. No toca el costo del producto: es por producto, no por almacén."""
        self.bloquear([x.producto_id for x in lineas])
        self._almacen(destino_id)
        ids = []
        for x in lineas:
            producto = self._producto(x.producto_id)
            almacen = self._almacen(x.almacen_id)
            for e, cant in self._asignar(x, producto, almacen, TRANSFERENCIA, hoy):
                self._repo.fijar_stock(e.id_, salir(e, cant).cantidad)
                self._repo.sumar_stock(x.producto_id, destino_id, e.lote_id, cp.cantidad(cant))
                costo = self._repo.costo(x.producto_id)
                monto = cp.importe(cp.cantidad(cant) * costo.promedio)
                for tipo, almacen_id in ((SALIDA, x.almacen_id), (ENTRADA, destino_id)):
                    ids.append(
                        self._registrar(
                            (ref_tipo, ref_id),
                            usuario_id,
                            costo,
                            monto,
                            tipo=tipo,
                            motivo=TRANSFERENCIA,
                            producto_id=x.producto_id,
                            almacen_id=almacen_id,
                            lote_id=e.lote_id,
                            cantidad=cant,
                            costo_unitario=costo.promedio,
                        )
                    )
        return ids

    def registrar_salida(
        self, motivo, ref_tipo, ref_id, lineas: list[Linea], usuario_id, hoy: date
    ) -> list[int]:
        """RF-INV-17, 19 y 22 a 24: con lote indicado, de ese lote; sin lote, por FEFO si el
        producto tiene stock con lote; si no, del stock sin lote."""
        self.bloquear([x.producto_id for x in lineas])
        ids = []
        for x in lineas:
            producto = self._producto(x.producto_id)
            almacen = self._almacen(x.almacen_id)
            asignaciones = self._asignar(x, producto, almacen, motivo, hoy)
            for e, cant in asignaciones:
                queda = salir(e, cant)  # RF-INV-19
                self._repo.fijar_stock(e.id_, queda.cantidad)
                antes = self._repo.costo(x.producto_id)
                despues, monto = cp.salida_al_promedio(antes, cant)
                ids.append(
                    self._registrar(
                        (ref_tipo, ref_id),
                        usuario_id,
                        despues,
                        monto,
                        tipo=SALIDA,
                        motivo=motivo,
                        producto_id=x.producto_id,
                        almacen_id=x.almacen_id,
                        lote_id=e.lote_id,
                        cantidad=cant,
                        costo_unitario=antes.promedio,
                    )
                )
        return ids

    def revertir(self, ref_tipo: str, ref_id: int, usuario_id: int | None) -> list[int]:
        """RF-INV-20 y 21: movimientos opuestos al costo original; una entrada ya consumida no
        se revierte (Q12 = A). Lo ya revertido no se vuelve a revertir. Una transferencia se
        revierte sin tocar el costo del producto (RF-INV-13)."""
        movs = self._repo.por_revertir(ref_tipo, ref_id)
        productos = sorted({m.producto_id for m in movs})
        self.bloquear(productos)
        for p in productos:
            propios = [m for m in movs if m.producto_id == p and m.motivo != TRANSFERENCIA]
            validar_reversion(self._repo.movimientos(p), propios)
        ids = []
        for inv in inversos_de(movs):
            antes = self._repo.costo(inv.producto_id)
            if inv.motivo == TRANSFERENCIA:
                despues, monto = antes, inv.costo_total
            elif inv.tipo == SALIDA:  # revierte una entrada
                despues, monto = cp.reversion_de_entrada(antes, inv.cantidad, inv.costo_unitario)
            else:  # revierte una salida: vuelve a entrar al costo con que salió
                despues = cp.entrada(antes, inv.cantidad, inv.costo_unitario)
                monto = despues.valor - antes.valor
            if inv.tipo == SALIDA:  # el stock de ese almacén y lote debe alcanzar (RF-INV-19)
                existencias = self._repo.existencias(inv.producto_id, inv.almacen_id)
                vacia = Existencia(Decimal("0"))
                e = next((e for e in existencias if e.lote_id == inv.lote_id), vacia)
                self._repo.fijar_stock(e.id_, salir(e, inv.cantidad).cantidad)
            else:
                self._repo.sumar_stock(inv.producto_id, inv.almacen_id, inv.lote_id, inv.cantidad)
            ids.append(
                self._registrar(
                    (ref_tipo, ref_id),
                    usuario_id,
                    despues,
                    monto,
                    tipo=inv.tipo,
                    motivo=ANULACION,
                    producto_id=inv.producto_id,
                    almacen_id=inv.almacen_id,
                    lote_id=inv.lote_id,
                    cantidad=inv.cantidad,
                    costo_unitario=inv.costo_unitario,
                    revierte_id=inv.revierte_id,
                )
            )
        return ids
