"""Maestro de tipos de documento de la plataforma (0006a, RF-VEN-49). Lo usa el super admin:
la vista lo protege con `solo_super`, como el resto de la plataforma."""

from collections.abc import Callable
from typing import Protocol

from shared.domain.documentos import ReglasDocumento, validar_reglas
from shared.domain.errores import DocumentoInvalido


class TiposDocumentoRepo(Protocol):
    def tipo(self, id_: int) -> ReglasDocumento: ...  # 404 si no existe
    def existe(self, campo: str, valor: str, excluir_id: int | None) -> bool: ...
    def guardar(self, id_: int | None, reglas: ReglasDocumento) -> int: ...


class GuardarTipoDocumento:
    """Crea o edita un tipo; la abreviatura y el código SUNAT no cambian una vez creados y el
    tipo no se elimina (se desactiva): así ningún contexto pierde el tipo de sus documentos."""

    def __init__(self, repo: TiposDocumentoRepo, atomic: Callable):
        self._repo, self._atomic = repo, atomic

    def ejecutar(self, id_: int | None, reglas: ReglasDocumento) -> int:
        reglas = validar_reglas(reglas)
        with self._atomic():
            if id_ is not None:
                actual = self._repo.tipo(id_)
                if (actual.abreviatura, actual.codigo_sunat) != (
                    reglas.abreviatura,
                    reglas.codigo_sunat,
                ):
                    raise DocumentoInvalido(
                        "La abreviatura y el código SUNAT no se cambian", "abreviatura"
                    )
            if self._repo.existe("abreviatura", reglas.abreviatura, id_):
                raise DocumentoInvalido(
                    f"Ya existe el tipo de documento {reglas.abreviatura}", "abreviatura"
                )
            if self._repo.existe("codigo_sunat", reglas.codigo_sunat, id_):
                raise DocumentoInvalido(
                    f"Ya existe un tipo de documento con el código SUNAT {reglas.codigo_sunat}",
                    "codigo_sunat",
                )
            return self._repo.guardar(id_, reglas)
