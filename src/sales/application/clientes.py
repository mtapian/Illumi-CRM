"""Clientes (spec 0006a, UC-VEN-01): crear, consultar y editar; no se eliminan (RF-VEN-05)."""

from collections.abc import Callable
from typing import Protocol

from sales.domain.cliente import DatosCliente, validar_cliente
from sales.domain.errores import ClienteInvalido
from shared.application.autorizacion import Actor, CasoDeUso
from shared.domain.documentos import ReglasDocumento
from shared.domain.errores import NoEncontrado

VER = "ventas.cliente.ver"
GESTIONAR = "ventas.cliente.gestionar"
GENERICO_ACTIVO = "Clientes varios no se desactiva"


class ClientesRepo(Protocol):
    def cliente(self, cliente_id: int) -> tuple[DatosCliente, bool] | None: ...  # y genérico
    def existe_documento(self, tipo: str, numero: str, excluir: int | None) -> bool: ...
    def guardar(self, cliente_id: int | None, datos: DatosCliente) -> int: ...
    def cambiar_estado(self, cliente_id: int, activo: bool) -> None: ...


class _Base(CasoDeUso):
    permiso_requerido = GESTIONAR

    def __init__(
        self,
        repo: ClientesRepo,
        documentos: Callable[[str], ReglasDocumento | None],
        atomic: Callable,
    ):
        self._repo, self._documentos, self._atomic = repo, documentos, atomic

    def _cliente(self, cliente_id: int) -> tuple[DatosCliente, bool]:
        actual = self._repo.cliente(cliente_id)
        if actual is None:
            raise NoEncontrado("El cliente no existe")
        return actual


class GuardarCliente(_Base):
    """RF-VEN-01, 02 y 50 (también el registro al vuelo): documento único en la empresa."""

    def ejecutar(self, actor: Actor, cliente_id: int | None, datos: DatosCliente) -> int:
        reglas = self._documentos(datos.tipo_doc)
        if cliente_id is not None:
            anterior, generico = self._cliente(cliente_id)
            if generico and not datos.activo:
                raise ClienteInvalido(GENERICO_ACTIVO, "activo")
            nuevo_tipo = datos.tipo_doc != anterior.tipo_doc
        else:
            nuevo_tipo = True
        if reglas is not None and not reglas.activo and nuevo_tipo:
            raise ClienteInvalido(f"El tipo de documento {reglas.nombre} está inactivo", "tipo_doc")
        datos = validar_cliente(datos, reglas)
        with self._atomic():
            if datos.num_doc and self._repo.existe_documento(
                datos.tipo_doc, datos.num_doc, cliente_id
            ):
                raise ClienteInvalido(
                    f"Ya existe un cliente con {datos.tipo_doc} {datos.num_doc}", "num_doc"
                )
            return self._repo.guardar(cliente_id, datos)


class CambiarEstadoCliente(_Base):
    """RF-VEN-05, 44: se desactiva o se reactiva; "Clientes varios" siempre activo."""

    def ejecutar(self, actor: Actor, cliente_id: int, activo: bool) -> None:
        _, generico = self._cliente(cliente_id)
        if generico and not activo:
            raise ClienteInvalido(GENERICO_ACTIVO)
        self._repo.cambiar_estado(cliente_id, activo)
