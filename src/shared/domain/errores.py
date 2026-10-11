"""Errores de negocio con código y mensaje para el usuario (plan 0000 §3 y §6)."""


class DomainError(Exception):
    codigo = "ERROR_DE_NEGOCIO"

    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje


class AccesoDenegado(DomainError):
    """El usuario no tiene el permiso de la acción (RF-TEN-49)."""

    codigo = "ACCESO_DENEGADO"


class FuncionalidadNoDisponible(AccesoDenegado):
    """El rol da el permiso, pero la funcionalidad ya no está habilitada (RF-TEN-42)."""

    codigo = "FUNCIONALIDAD_NO_DISPONIBLE"


class NoEncontrado(DomainError):
    """El registro no existe o es de otra empresa: no se revela cuál (RF-TEN-52)."""

    codigo = "NO_ENCONTRADO"


class DocumentoInvalido(DomainError):
    """RUC o DNI mal formado (RF-TEN-03, RF-COM-01)."""

    codigo = "DOCUMENTO_INVALIDO"
