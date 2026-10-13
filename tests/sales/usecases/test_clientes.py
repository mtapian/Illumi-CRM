"""0006a, T5: clientes CRU, sin eliminar, y búsqueda (RF-VEN-01, 02, 05, 44, 50)."""

from dataclasses import replace

import pytest

from sales.application import clientes as uc
from sales.domain.cliente import DatosCliente
from sales.domain.errores import ClienteInvalido
from sales.infrastructure.contenedor import buscar_clientes, caso_de_cliente
from sales.infrastructure.models import Cliente
from shared.application.autorizacion import Actor
from shared.domain.errores import AccesoDenegado, DocumentoInvalido

pytestmark = pytest.mark.django_db
BAR = DatosCliente("Bar El Lúpulo", "RUC", "20512345671", telefono="987654321")


def guardar(actor, datos, id_=None):
    return caso_de_cliente(uc.GuardarCliente).ejecutar(actor, id_, datos)


def test_crear_editar_y_buscar(empresa_ventas):
    _, actor = empresa_ventas
    id_ = guardar(actor, replace(BAR, email=" bar@lupulo.pe ", canal="B2B"))
    c = Cliente.objects.get(pk=id_)
    assert (c.num_doc, c.email, c.canal, c.activo) == ("20512345671", "bar@lupulo.pe", "B2B", True)
    guardar(actor, replace(BAR, nombre="Bar El Lúpulo SAC"), id_)
    assert Cliente.objects.get(pk=id_).nombre == "Bar El Lúpulo SAC"
    ana = guardar(actor, DatosCliente("Ana Quispe", "DNI", "45871236"))  # datos mínimos
    assert [x.nombre for x in buscar_clientes(empresa_ventas[0].id, "lúpulo")] == [
        "Bar El Lúpulo SAC"
    ]
    assert [x.id for x in buscar_clientes(empresa_ventas[0].id, "4587")] == [ana]
    caso_de_cliente(uc.CambiarEstadoCliente).ejecutar(actor, ana, False)
    assert buscar_clientes(empresa_ventas[0].id, "Ana") == []  # inactivo no se ofrece (RF-VEN-44)


@pytest.mark.parametrize(
    "datos, excepcion, mensaje",
    [
        (replace(BAR, num_doc="20512345670"), DocumentoInvalido, "El RUC no es válido"),
        (replace(BAR, nombre=" "), ClienteInvalido, "El nombre o razón social es obligatorio"),
        (replace(BAR, email="no-es-un-email"), ClienteInvalido, "El email no es válido"),
        (DatosCliente("Turista", "SD", "123"), DocumentoInvalido, "Sin documento no lleva número"),
        (replace(BAR, tipo_doc="XX"), ClienteInvalido, "Elige un tipo de documento"),
        (replace(BAR, canal="B2X"), ClienteInvalido, "El canal debe ser B2B o B2C"),
    ],
)
def test_datos_invalidos(empresa_ventas, datos, excepcion, mensaje):
    with pytest.raises(excepcion, match=mensaje):
        guardar(empresa_ventas[1], datos)


def test_documento_unico_y_genericos(empresa_ventas):
    _, actor = empresa_ventas
    guardar(actor, BAR)
    with pytest.raises(ClienteInvalido, match="Ya existe un cliente con RUC 20512345671"):
        guardar(actor, replace(BAR, nombre="Otro bar"))
    guardar(actor, DatosCliente("Turista 1", "SD"))
    guardar(actor, DatosCliente("Turista 2", "SD"))  # sin número: no se repite
    generico = Cliente.objects.get(es_generico=True).id
    with pytest.raises(ClienteInvalido, match="Clientes varios no se desactiva"):
        caso_de_cliente(uc.CambiarEstadoCliente).ejecutar(actor, generico, False)


def test_permiso(empresa_ventas):
    _, actor = empresa_ventas
    sin = Actor(actor.usuario_id, actor.empresa_id, actor.permisos - {uc.GESTIONAR})
    with pytest.raises(AccesoDenegado):
        guardar(sin, BAR)
