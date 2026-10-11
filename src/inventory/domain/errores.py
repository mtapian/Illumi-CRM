from shared.domain.errores import DomainError


class StockInsuficiente(DomainError):
    codigo = "STOCK_INSUFICIENTE"


class LoteVencido(DomainError):
    codigo = "LOTE_VENCIDO"


class AnulacionConConsumoPosterior(DomainError):
    codigo = "ANULACION_CON_CONSUMO_POSTERIOR"


class ServicioSinStock(DomainError):
    codigo = "SERVICIO_SIN_STOCK"


class LoteConOtroVencimiento(DomainError):
    codigo = "LOTE_CON_OTRO_VENCIMIENTO"
