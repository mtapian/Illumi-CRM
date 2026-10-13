from shared.domain.errores import DomainError


class ClienteInvalido(DomainError):
    codigo = "CLIENTE_INVALIDO"


class PedidoInvalido(DomainError):
    codigo = "PEDIDO_INVALIDO"


class CobranzaInvalida(DomainError):
    codigo = "COBRANZA_INVALIDA"
