"""Tipos de producto y lo que cada uno permite (spec 0002a, "Definiciones")."""

from enum import StrEnum


class TipoProducto(StrEnum):
    INSUMO = "INSUMO"
    ENVASE = "ENVASE"
    GRANEL = "GRANEL"
    TERMINADO = "TERMINADO"
    MERCADERIA = "MERCADERIA"

    @property
    def comprable(self) -> bool:
        return self in (TipoProducto.INSUMO, TipoProducto.ENVASE, TipoProducto.MERCADERIA)

    @property
    def producible(self) -> bool:
        return self in (TipoProducto.GRANEL, TipoProducto.TERMINADO)

    @property
    def vendible(self) -> bool:
        """Solo estos tienen precio y se venden (RF-CAT-13, RN-CAT-06)."""
        return self in (TipoProducto.TERMINADO, TipoProducto.MERCADERIA)

    @property
    def lote_siempre(self) -> bool:
        """Siempre con lote; la mercadería, solo si se eligió (RF-CAT-12, RN-CAT-03)."""
        return self in (TipoProducto.GRANEL, TipoProducto.TERMINADO)
