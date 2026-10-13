"""Pedidos (spec 0006a, UC-VEN-02 a 05): crear, editar, aprobar (exige stock) y cancelar.
Facturar y entregar son de 0006b."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date
from typing import Protocol

from catalog.application.fachada import CatalogoQuery
from inventory.application.servicio import InventarioService
from sales.domain.errores import PedidoInvalido
from sales.domain.pedido import CREADO, LineaPedido, total, transicion, validar_lineas
from shared.application.autorizacion import Actor, CasoDeUso
from shared.application.puertos import SequencePort
from shared.domain.stock import faltantes

VER = "ventas.pedido.ver"
GESTIONAR = "ventas.pedido.gestionar"
CANCELAR = "ventas.pedido.cancelar"


@dataclass(frozen=True)
class DatosPedido:
    cliente_id: int | None
    fecha_entrega: date
    comentario: str = ""
    lineas: tuple[LineaPedido, ...] = ()


class PedidosRepo(Protocol):
    def cliente_activo(self, cliente_id: int) -> bool: ...
    def crear(self, numero: int, datos: DatosPedido, total, usuario_id: int, token) -> int: ...
    def actualizar(self, pedido_id: int, datos: DatosPedido, total, lineas: bool) -> None: ...
    def bloquear(self, pedido_id: int) -> tuple[str, DatosPedido]: ...  # FOR UPDATE; 404
    def aprobar(self, pedido_id: int, usuario_id: int) -> None: ...
    def cancelar(self, pedido_id: int, usuario_id: int, motivo: str) -> None: ...


class _Base(CasoDeUso):
    permiso_requerido = GESTIONAR

    def __init__(
        self,
        repo: PedidosRepo,
        catalogo: CatalogoQuery,
        inventario: InventarioService,
        secuencia: SequencePort,
        atomic: Callable,
    ):
        self._repo, self._catalogo, self._inv = repo, catalogo, inventario
        self._secuencia, self._atomic = secuencia, atomic

    def _validar(self, datos: DatosPedido, para_aprobar: bool = False) -> DatosPedido:
        """RF-VEN-06, 08, 44: cliente activo, productos vendibles y líneas válidas."""
        if not datos.cliente_id or not self._repo.cliente_activo(datos.cliente_id):
            raise PedidoInvalido("El cliente no existe o está inactivo", "cliente")
        validar_lineas(datos.lineas, para_aprobar)
        for x in datos.lineas:
            p = self._catalogo.producto(x.producto_id)
            if p is None or not (p.activo and p.se_vende):
                sku = p.sku if p else x.producto_id
                raise PedidoInvalido(f"{sku} no se vende o está inactivo", "lineas")
        return replace(datos, comentario=datos.comentario.strip())


class CrearPedido(_Base):
    """RF-VEN-06: queda Creado, con número correlativo."""

    def ejecutar(self, actor: Actor, datos: DatosPedido) -> int:
        with self._atomic():
            return self.crear(actor, datos)

    def crear(self, actor: Actor, datos: DatosPedido, token=None) -> int:
        """Dentro de una transacción abierta (también la usa la venta directa, 0006b)."""
        datos = self._validar(datos)
        numero = self._secuencia.siguiente("PEDIDO")
        return self._repo.crear(numero, datos, total(datos.lineas), actor.usuario_id, token)


class EditarPedido(_Base):
    """RF-VEN-07 y 11: Creado, todo; Aprobado, solo fecha de entrega y comentario."""

    def ejecutar(self, actor: Actor, pedido_id: int, datos: DatosPedido) -> None:
        with self._atomic():
            estado, actual = self._repo.bloquear(pedido_id)
            cambia_lineas = (datos.cliente_id, datos.lineas) != (actual.cliente_id, actual.lineas)
            completo = (
                cambia_lineas or estado == CREADO
            )  # Creado: todo; Aprobado: fecha y comentario
            transicion(estado, "editar" if completo else "editar_fecha")
            if completo:
                datos = self._validar(datos)
            else:
                datos = replace(
                    actual, fecha_entrega=datos.fecha_entrega, comentario=datos.comentario.strip()
                )
            self._repo.actualizar(pedido_id, datos, total(datos.lineas), completo)


class AprobarPedido(_Base):
    """RF-VEN-08: exige stock suficiente; facturar (0006b) lo vuelve a validar (art. 10.3)."""

    def ejecutar(self, actor: Actor, pedido_id: int, hoy: date) -> None:
        with self._atomic():
            estado, datos = self._repo.bloquear(pedido_id)
            transicion(estado, "aprobar")
            self._validar(datos, para_aprobar=True)
            bienes = {}
            for x in datos.lineas:
                p = self._catalogo.producto(x.producto_id)
                if p.tipo != "SERVICIO":
                    bienes[p.sku] = (p.id, x.cantidad)
            disponibles = self._inv.disponibles([i for i, _ in bienes.values()], hoy)
            mensaje = faltantes(
                {sku: q for sku, (_, q) in bienes.items()},
                {sku: disponibles[i] for sku, (i, _) in bienes.items()},
            )
            if mensaje:
                raise PedidoInvalido(mensaje, "lineas")
            self._repo.aprobar(pedido_id, actor.usuario_id)


class CancelarPedido(_Base):
    """RF-VEN-37: Creado o Aprobado, con motivo."""

    permiso_requerido = CANCELAR

    def ejecutar(self, actor: Actor, pedido_id: int, motivo: str) -> None:
        if not motivo.strip():
            raise PedidoInvalido("Indica el motivo de la cancelación", "motivo")
        with self._atomic():
            estado, _ = self._repo.bloquear(pedido_id)
            transicion(estado, "cancelar")
            self._repo.cancelar(pedido_id, actor.usuario_id, motivo.strip())
