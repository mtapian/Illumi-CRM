from shared.domain.errores import DomainError


class ProveedorInvalido(DomainError):
    codigo = "PROVEEDOR_INVALIDO"
