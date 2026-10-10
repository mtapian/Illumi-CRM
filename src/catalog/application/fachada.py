"""Fachada pública del catálogo para los demás contextos (plan 0002a §1)."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from catalog.domain.errores import IscSinTarifaVigente
from catalog.domain.isc import Tarifa, isc_linea, tarifa_aplicable
from catalog.domain.presentacion import DatosPresentacion, materiales_para
from catalog.domain.tipos import TipoProducto


@dataclass(frozen=True)
class ProductoDTO:
    id: int
    sku: str
    nombre: str
    tipo: TipoProducto
    unidad: str
    controla_lote: bool
    precio_venta: Decimal | None
    activo: bool


@dataclass(frozen=True)
class IscDTO:
    """Lo que necesitan ventas y facturación para una línea con ISC (RF-CAT-25)."""

    monto_por_litro: Decimal
    contenido_litros: Decimal
    codigo_tributo: str
    codigo_tipo_sistema: str


class ConsultaRepo(Protocol):
    def productos(self, ids=None, tipos=None, solo_activos=False) -> list[ProductoDTO]: ...
    def presentacion(self, producto_id: int) -> DatosPresentacion | None: ...
    def isc_de_producto(self, producto_id: int): ...
    def tarifas_isc(self, categoria_id: int) -> list[Tarifa]: ...


class CatalogoQuery:
    def __init__(self, repo: ConsultaRepo):
        self._repo = repo

    def producto(self, producto_id: int) -> ProductoDTO | None:
        """Incluye inactivos: el historial y los reportes los siguen mostrando (RF-CAT-19)."""
        filas = self._repo.productos(ids=[producto_id])
        return filas[0] if filas else None

    def activos(self, tipos: Iterable[TipoProducto] | None = None) -> list[ProductoDTO]:
        """Lo que se ofrece en operaciones nuevas: compras, recetas, envasados, ventas."""
        return self._repo.productos(tipos=tipos, solo_activos=True)

    def presentacion(self, producto_id: int) -> DatosPresentacion | None:
        return self._repo.presentacion(producto_id)

    def materiales_para(self, producto_id: int, unidades: Decimal) -> dict[int, Decimal]:
        """Materiales que consume envasar `unidades` del terminado (lo usa la épica 0005b)."""
        p = self._repo.presentacion(producto_id)
        return materiales_para(dict(p.materiales), unidades) if p else {}

    def isc_aplicable(self, producto_id: int, fecha: date) -> IscDTO | None:
        """None si el producto no tiene categoría (RF-CAT-27); la tarifa vigente a la fecha
        de emisión si la tiene (RF-CAT-25)."""
        datos = self._repo.isc_de_producto(producto_id)
        if datos is None:
            return None
        categoria, contenido = datos
        tarifa = tarifa_aplicable(self._repo.tarifas_isc(categoria.id), fecha)
        if tarifa is None:
            raise IscSinTarifaVigente(
                f"La categoría de ISC {categoria} no tiene tarifa vigente al {fecha:%Y-%m-%d}"
            )
        return IscDTO(
            tarifa.monto_por_litro,
            contenido,
            categoria.codigo_tributo,
            categoria.codigo_tipo_sistema,
        )

    def isc_de_linea(self, producto_id: int, cantidad: Decimal, fecha: date) -> Decimal:
        isc = self.isc_aplicable(producto_id, fecha)
        if isc is None:
            return isc_linea(cantidad, Decimal("0"), None)
        return isc_linea(cantidad, isc.contenido_litros, Tarifa(fecha, isc.monto_por_litro))
