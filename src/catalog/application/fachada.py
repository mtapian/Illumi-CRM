"""Fachada pública del catálogo para los demás contextos (plan 0002a §1)."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

from catalog.domain.errores import ImpuestoInvalido, IscSinTarifaVigente
from catalog.domain.impuestos import AFECTACION, COMPRA, FIJO, ISC, VENTA, Tasa, desglose_linea
from catalog.domain.isc import CODIGO_TRIBUTO, Tarifa, isc_linea, tarifa_aplicable
from catalog.domain.precio import Desglose
from catalog.domain.receta import Receta, componentes_para
from catalog.domain.tipos import TipoProducto
from shared.domain.vigencia import SinValorVigente, valor_vigente


@dataclass(frozen=True)
class ProductoDTO:
    id: int
    sku: str
    nombre: str
    tipo: TipoProducto
    unidad: str
    se_vende: bool
    se_compra: bool
    se_fabrica: bool
    precio_venta: Decimal | None
    activo: bool
    vida_util_dias: int | None = None  # sugiere el vencimiento del lote (RF-CAT-40)


@dataclass(frozen=True)
class EntradaHistorial:
    """Una fila del historial del producto, lista para mostrar (RF-CAT-32)."""

    fecha: datetime
    autor: str
    accion: str
    cambios: list[str]


@dataclass(frozen=True)
class IscDTO:
    """Lo que necesitan ventas y facturación para una línea con ISC (RF-CAT-25)."""

    monto_por_litro: Decimal
    contenido_litros: Decimal
    codigo_tributo: str
    codigo_tipo_sistema: str


class ConsultaRepo(Protocol):
    def productos(self, ids=None, casillas=None, solo_activos=False) -> list[ProductoDTO]: ...
    def receta(self, producto_id: int) -> Receta: ...
    def isc_de_producto(self, producto_id: int) -> tuple[str, Decimal] | None: ...
    def tasas_isc(self, producto_id: int) -> list[Tarifa]: ...
    def impuestos_del_producto(self, producto_id: int, tipo: str) -> list: ...


class CatalogoQuery:
    def __init__(self, repo: ConsultaRepo):
        self._repo = repo

    def producto(self, producto_id: int) -> ProductoDTO | None:
        """Incluye inactivos: el historial y los reportes los siguen mostrando (RF-CAT-19)."""
        filas = self._repo.productos(ids=[producto_id])
        return filas[0] if filas else None

    def activos(self, **casillas: bool) -> list[ProductoDTO]:
        """Lo que se ofrece en operaciones nuevas, p. ej. `activos(se_vende=True)` en ventas,
        `activos(se_compra=True)` en compras (RF-CAT-39)."""
        return self._repo.productos(casillas=casillas, solo_activos=True)

    def receta(self, producto_id: int) -> Receta:
        """Vacía si el producto no tiene receta (es opcional; RF-CAT-41)."""
        return self._repo.receta(producto_id)

    def componentes_para(self, producto_id: int, cantidad: Decimal) -> dict[int, Decimal]:
        """Componentes de la receta para producir `cantidad`: la OP los copia (0005a)."""
        return componentes_para(self._repo.receta(producto_id), cantidad)

    def isc_aplicable(self, producto_id: int, fecha: date) -> IscDTO | None:
        """None si el producto no está afecto (RF-CAT-27); la tasa vigente a la fecha de
        emisión si lo está (RF-CAT-25, 46)."""
        datos = self._repo.isc_de_producto(producto_id)
        if datos is None:
            return None
        codigo_tipo_sistema, contenido = datos
        tarifa = tarifa_aplicable(self._repo.tasas_isc(producto_id), fecha)
        if tarifa is None:
            raise IscSinTarifaVigente(
                f"El producto no tiene tasa de ISC vigente al {fecha:%Y-%m-%d}"
            )
        return IscDTO(tarifa.monto_por_litro, contenido, CODIGO_TRIBUTO, codigo_tipo_sistema)

    def _vigentes(self, producto_id: int, tipo: str, fecha: date) -> dict[str, Tasa]:
        """Código → (criterio, importe vigente) de los impuestos del producto (RF-CAT-59)."""
        vigentes = {}
        for nombre, codigo, criterio, tasas in self._repo.impuestos_del_producto(producto_id, tipo):
            try:
                vigentes[codigo] = (criterio, valor_vigente(tasas, fecha))
            except SinValorVigente:
                raise ImpuestoInvalido(
                    f"El impuesto {nombre} no tiene tasa vigente al {fecha:%Y-%m-%d}"
                ) from None
        return vigentes

    def desglose_de_linea(
        self, producto_id: int, total: Decimal, cantidad: Decimal, fecha: date
    ) -> Desglose:
        """Valor, ISC e IGV de una línea de venta con precio que incluye impuestos (RF-CAT-59)."""
        vigentes = self._vigentes(producto_id, VENTA, fecha)
        afectacion = next((vigentes[c] for c in AFECTACION if c in vigentes), None)
        if afectacion is None:
            raise ImpuestoInvalido("El producto no tiene impuesto de IGV, exonerado o inafecto")
        return desglose_linea(total, cantidad, afectacion, vigentes.get(ISC))

    def igv_de_compra(self, producto_id: int, fecha: date) -> Tasa | None:
        """(criterio, importe) de la afectación de compra a la fecha; None si el producto aún
        no tiene impuestos de compra (RF-CAT-61)."""
        vigentes = self._vigentes(producto_id, COMPRA, fecha)
        return next((vigentes[c] for c in AFECTACION if c in vigentes), None)

    def isc_de_linea(self, producto_id: int, cantidad: Decimal, fecha: date) -> Decimal:
        """Con un ISC de monto fijo entre sus impuestos de venta, cantidad × monto; un ISC
        porcentual depende del precio: usar `desglose_de_linea`."""
        criterio, importe = self._vigentes(producto_id, VENTA, fecha).get(ISC, (None, None))
        if criterio == FIJO:
            return (cantidad * importe).quantize(Decimal("0.01"), ROUND_HALF_UP)
        if criterio is not None:
            raise ImpuestoInvalido("El ISC porcentual depende del precio de la línea")
        # ponytail: ISC por litro de la enmienda 4 hasta la conversión de T6 (RF-CAT-60).
        isc = self.isc_aplicable(producto_id, fecha)
        if isc is None:
            return isc_linea(cantidad, Decimal("0"), None)
        return isc_linea(cantidad, isc.contenido_litros, Tarifa(fecha, isc.monto_por_litro))
