from shared.domain.errores import DomainError


class RucInvalido(DomainError):
    codigo = "RUC_INVALIDO"


class IgvInvalido(DomainError):
    codigo = "IGV_INVALIDO"


class RucDuplicado(DomainError):
    codigo = "RUC_DUPLICADO"


class EmailDuplicado(DomainError):
    codigo = "EMAIL_DUPLICADO"


class SinPlanDePrueba(DomainError):
    codigo = "SIN_PLAN_DE_PRUEBA"


class DependenciasFaltantes(DomainError):
    codigo = "DEPENDENCIAS_FALTANTES"


class DependientesHabilitados(DomainError):
    codigo = "DEPENDIENTES_HABILITADOS"


class MotivoObligatorio(DomainError):
    codigo = "MOTIVO_OBLIGATORIO"


class CoreNoSeQuita(DomainError):
    codigo = "CORE_NO_SE_QUITA"


class EscaladaDePrivilegios(DomainError):
    codigo = "ESCALADA_DE_PRIVILEGIOS"


class PermisoNoHabilitado(DomainError):
    codigo = "PERMISO_NO_HABILITADO"


class LimiteUsuariosPlan(DomainError):
    codigo = "LIMITE_USUARIOS_PLAN"


class UltimoAdministrador(DomainError):
    codigo = "ULTIMO_ADMINISTRADOR"


class RolDeSistema(DomainError):
    codigo = "ROL_DE_SISTEMA"


class RolConUsuarios(DomainError):
    codigo = "ROL_CON_USUARIOS"


class SinApiIntegracion(DomainError):
    codigo = "SIN_API_INTEGRACION"


class EmpresaNoOperativa(DomainError):
    codigo = "EMPRESA_NO_OPERATIVA"
