from shared.domain.errores import DomainError


class ProveedorInvalido(DomainError):
    codigo = "PROVEEDOR_INVALIDO"


class CompraInvalida(DomainError):
    codigo = "COMPRA_INVALIDA"
