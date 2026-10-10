"""Empresa (tenant) de la operación en curso (plan 0000 §4)."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_empresa: ContextVar[int | None] = ContextVar("empresa_actual", default=None)


class TenantNoDefinido(Exception):
    """Se intentó leer o escribir datos de negocio sin elegir una empresa."""


def empresa_actual() -> int:
    empresa_id = _empresa.get()
    if empresa_id is None:
        raise TenantNoDefinido("No hay una empresa seleccionada para esta operación")
    return empresa_id


@contextmanager
def tenant_context(empresa_id: int) -> Iterator[None]:
    token = _empresa.set(empresa_id)
    try:
        yield
    finally:
        _empresa.reset(token)
