"""Autorización en el servidor (spec 0001c; RF-TEN-49, RNF-TEN-06).

Todo caso de uso hereda de `CasoDeUso` y declara `permiso_requerido`; su `ejecutar(actor, …)`
verifica el permiso antes de hacer nada. Ocultar un botón no es control de acceso.
"""

from dataclasses import dataclass, field
from functools import wraps

from shared.domain.errores import AccesoDenegado, FuncionalidadNoDisponible

ACCESO_DENEGADO = "Acceso denegado"
NO_DISPONIBLE = "Esta funcionalidad ya no está disponible en tu plan"


@dataclass(frozen=True)
class Actor:
    usuario_id: int
    empresa_id: int
    permisos: frozenset[str]  # efectivos: roles ∩ habilitados
    permisos_rol: frozenset[str] = field(default_factory=frozenset)  # lo que dan sus roles
    es_admin: bool = False

    def puede(self, permiso: str) -> bool:
        return permiso in self.permisos

    def exige(self, permiso: str) -> None:
        if permiso in self.permisos:
            return
        if permiso in self.permisos_rol:
            raise FuncionalidadNoDisponible(NO_DISPONIBLE)
        raise AccesoDenegado(ACCESO_DENEGADO)


class CasoDeUso:
    permiso_requerido: str

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        original = cls.__dict__.get("ejecutar")
        if original is None:
            return
        permiso = cls.permiso_requerido

        @wraps(original)
        def ejecutar(self, actor: Actor, *args, **kw):
            actor.exige(permiso)
            return original(self, actor, *args, **kw)

        cls.ejecutar = ejecutar
