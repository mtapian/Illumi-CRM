from shared.domain.errores import DomainError


class ProductoInvalido(DomainError):
    codigo = "PRODUCTO_INVALIDO"


class SkuDuplicado(DomainError):
    codigo = "SKU_DUPLICADO"


class CampoInmutable(DomainError):
    codigo = "CAMPO_INMUTABLE"


class LimiteProductosPlan(DomainError):
    codigo = "LIMITE_PRODUCTOS_PLAN"


class NoSePuedeDesactivar(DomainError):
    codigo = "NO_SE_PUEDE_DESACTIVAR"


class NoSePuedeEliminar(DomainError):
    codigo = "NO_SE_PUEDE_ELIMINAR"


class UnidadInvalida(DomainError):
    codigo = "UNIDAD_INVALIDA"


class RecetaInvalida(DomainError):
    codigo = "RECETA_INVALIDA"


class CodigoBarrasDuplicado(DomainError):
    codigo = "CODIGO_BARRAS_DUPLICADO"


class AgrupacionInvalida(DomainError):
    codigo = "AGRUPACION_INVALIDA"


class ImpuestoInvalido(DomainError):
    codigo = "IMPUESTO_INVALIDO"
