from shared.domain.errores import DomainError


class StockInsuficiente(DomainError):
    codigo = "STOCK_INSUFICIENTE"


class LoteVencido(DomainError):
    codigo = "LOTE_VENCIDO"


class AnulacionConConsumoPosterior(DomainError):
    codigo = "ANULACION_CON_CONSUMO_POSTERIOR"

    def __init__(self, mensaje: str, producto_id: int | None = None):
        super().__init__(mensaje)
        self.producto_id = producto_id  # para que quien anula nombre el producto (RF-COM-16)


class ServicioSinStock(DomainError):
    codigo = "SERVICIO_SIN_STOCK"


class LoteConOtroVencimiento(DomainError):
    codigo = "LOTE_CON_OTRO_VENCIMIENTO"


class CostoRequerido(DomainError):
    codigo = "COSTO_REQUERIDO"


class AlmacenInvalido(DomainError):
    codigo = "ALMACEN_INVALIDO"


class AjusteInvalido(DomainError):
    codigo = "AJUSTE_INVALIDO"
