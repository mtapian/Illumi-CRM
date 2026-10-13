"""Facturar y entregar un pedido (spec 0006b, UC-VEN-05). La venta es el pedido facturado:
facturar vuelve a validar (art. 10.3), saca el stock, congela el costo, calcula el desglose
(comprobante pendiente para 0007a) y crea la cobranza, todo en una transacción."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol

from catalog.application.fachada import CatalogoQuery
from inventory.application.servicio import InventarioService, Linea
from sales.application.cobranzas import DatosPago, RegistrarPago
from sales.application.pedidos import CrearPedido, DatosPedido
from sales.domain import facturacion as f
from sales.domain.errores import PedidoInvalido
from sales.domain.pedido import LineaPedido, subtotal, total, transicion
from shared.application.autorizacion import Actor, CasoDeUso
from shared.domain.stock import faltantes

REGISTRAR = "ventas.venta.registrar"
SERVICIO = "SERVICIO"


@dataclass(frozen=True)
class DatosFactura:
    almacen_id: int
    forma_pago: str = f.CONTADO
    cuotas: tuple[f.Cuota, ...] = ()
    lotes: dict[int, str] = field(default_factory=dict)  # producto → lote elegido (RF-VEN-20)


@dataclass(frozen=True)
class LineaFacturada:
    producto_id: int
    valor: Decimal
    isc: Decimal
    igv: Decimal
    costo: Decimal


class FacturasRepo(Protocol):
    def bloquear(self, pedido_id: int): ...  # (estado, DatosPedido); FOR UPDATE; 404
    def cliente(self, cliente_id: int) -> tuple[str, bool, bool]: ...  # tipo_doc, genérico, activo
    def facturar(
        self, pedido_id, comprobante, forma_pago, almacen_id, emision, lineas, usuario_id
    ) -> None: ...
    def crear_cobranza(self, pedido_id, cliente_id, total, emision, cuotas) -> int: ...
    def entregar(self, pedido_id: int, usuario_id: int) -> None: ...
    def aprobar(self, pedido_id: int, usuario_id: int) -> None: ...
    def por_token(self, token) -> int | None: ...
    def cobranza_de(self, pedido_id: int) -> int: ...


class _Base(CasoDeUso):
    permiso_requerido = REGISTRAR

    def __init__(
        self,
        repo: FacturasRepo,
        catalogo: CatalogoQuery,
        inventario: InventarioService,
        umbral_boleta: Callable[[date], Decimal],
        atomic: Callable,
    ):
        self._repo, self._catalogo, self._inv = repo, catalogo, inventario
        self._umbral, self._atomic = umbral_boleta, atomic


class FacturarPedido(_Base):
    """RF-VEN-17, 19 a 28 y 38."""

    def ejecutar(self, actor: Actor, pedido_id: int, datos: DatosFactura, hoy: date) -> None:
        with self._atomic():
            self.facturar(actor, pedido_id, datos, hoy)

    def facturar(self, actor: Actor, pedido_id: int, datos: DatosFactura, hoy: date) -> None:
        """Dentro de una transacción abierta (también la usa la venta directa)."""
        estado, pedido = self._repo.bloquear(pedido_id)
        transicion(estado, "facturar")
        tipo_doc, generico, activo = self._repo.cliente(pedido.cliente_id)
        if not activo:
            raise PedidoInvalido("El cliente está inactivo", "cliente")
        importe = total(pedido.lineas)
        comprobante = f.comprobante_para(tipo_doc)
        if comprobante == f.BOLETA:
            f.validar_boleta(generico, importe, self._umbral(hoy))
        cuotas = f.cronograma(datos.forma_pago, comprobante, datos.cuotas, importe, hoy)

        productos = {x.producto_id: self._catalogo.producto(x.producto_id) for x in pedido.lineas}
        for p in productos.values():  # RF-VEN-23: doble validación
            if not (p.activo and p.se_vende):
                raise PedidoInvalido(f"{p.sku} ya no se vende", "lineas")
        desgloses = {}
        for x in pedido.lineas:
            d = self._catalogo.desglose_de_linea(x.producto_id, subtotal(x), x.cantidad, hoy)
            f.validar_valor(productos[x.producto_id].sku, d.valor)
            desgloses[x.producto_id] = d

        bienes = [x for x in pedido.lineas if productos[x.producto_id].tipo != SERVICIO]
        self._inv.bloquear([x.producto_id for x in bienes])  # antes de mirar el stock
        requeridos, disponibles = {}, {}
        for x in bienes:
            lote = datos.lotes.get(x.producto_id)
            sku = productos[x.producto_id].sku
            clave = f"{sku} ({lote})" if lote else sku
            orden = self._inv.existencias_en_orden(x.producto_id, datos.almacen_id, hoy)
            requeridos[clave] = x.cantidad
            disponibles[clave] = sum(
                (q for codigo, q in orden if not lote or codigo == lote), f.CERO
            )
        mensaje = faltantes(requeridos, disponibles)  # RF-VEN-26: todos los faltantes
        if mensaje:
            raise PedidoInvalido(mensaje, "lineas")

        facturadas = []
        for x in pedido.lineas:
            costo = f.CERO
            if productos[x.producto_id].tipo != SERVICIO:
                linea = Linea(
                    x.producto_id, datos.almacen_id, x.cantidad, lote=datos.lotes.get(x.producto_id)
                )
                ids = self._inv.registrar_salida(
                    "VENTA", "VENTA", pedido_id, [linea], actor.usuario_id, hoy
                )
                costo = sum((c.importe for c in self._inv.consumido(ids)), f.CERO)  # RF-VEN-21
            d = desgloses[x.producto_id]
            facturadas.append(LineaFacturada(x.producto_id, d.valor, d.isc, d.igv, costo))
        self._repo.facturar(
            pedido_id,
            comprobante,
            datos.forma_pago,
            datos.almacen_id,
            hoy,
            facturadas,
            actor.usuario_id,
        )
        self._repo.crear_cobranza(pedido_id, pedido.cliente_id, importe, hoy, cuotas)


class EntregarPedido(_Base):
    """RF-VEN-51: no depende de la cobranza."""

    def ejecutar(self, actor: Actor, pedido_id: int) -> None:
        with self._atomic():
            estado, _ = self._repo.bloquear(pedido_id)
            transicion(estado, "entregar")
            self._repo.entregar(pedido_id, actor.usuario_id)


@dataclass(frozen=True)
class DatosVentaDirecta:
    cliente_id: int
    almacen_id: int
    lineas: tuple[LineaPedido, ...]
    pagos: tuple[tuple[int, Decimal], ...]  # (método, monto)
    token: object  # UUID del formulario (RF-VEN-29)
    lotes: dict[int, str] = field(default_factory=dict)


class VentaDirecta(CasoDeUso):
    """RF-VEN-18, 29 y 52: crea el pedido, lo factura al contado, registra los pagos y lo
    entrega, en una transacción. Reutiliza los casos de uso por dentro (sin sus permisos:
    la venta directa exige `ventas.venta.registrar`)."""

    permiso_requerido = REGISTRAR

    def __init__(
        self,
        repo: FacturasRepo,
        crear: CrearPedido,
        facturar: FacturarPedido,
        pagar: RegistrarPago,
        atomic: Callable,
    ):
        self._repo, self._crear, self._facturar, self._pagar = repo, crear, facturar, pagar
        self._atomic = atomic

    def ejecutar(self, actor: Actor, datos: DatosVentaDirecta, hoy: date) -> int:
        f.validar_pagos_directa([m for _, m in datos.pagos], total(datos.lineas))
        with self._atomic():
            # ponytail: dos envíos simultáneos con el mismo token chocan en el índice único
            # (error); el reenvío habitual llega después y devuelve la venta registrada.
            existente = self._repo.por_token(datos.token)
            if existente:
                return existente
            pedido = DatosPedido(datos.cliente_id, hoy, "", datos.lineas)
            pedido_id = self._crear.crear(actor, pedido, datos.token)
            self._repo.aprobar(pedido_id, actor.usuario_id)
            factura = DatosFactura(datos.almacen_id, f.CONTADO, (), datos.lotes)
            self._facturar.facturar(actor, pedido_id, factura, hoy)
            cobranza_id = self._repo.cobranza_de(pedido_id)
            for metodo_id, monto in datos.pagos:
                self._pagar.registrar(actor, cobranza_id, DatosPago(metodo_id, monto, hoy), hoy)
            self._repo.entregar(pedido_id, actor.usuario_id)
            return pedido_id
