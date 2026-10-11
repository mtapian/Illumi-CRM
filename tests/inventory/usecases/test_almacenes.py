"""0003a, T16: almacenes (RF-INV-02, RF-INV-03)."""

from datetime import date
from decimal import Decimal as D

import pytest
from django.db import transaction

from inventory.application import almacenes as uc
from inventory.application.servicio import Linea
from inventory.domain.errores import AlmacenInvalido
from inventory.infrastructure.contenedor import caso_de_uso, inventario
from inventory.infrastructure.models import Almacen
from tenancy.infrastructure.contenedor import actor_de

pytestmark = pytest.mark.django_db


@pytest.fixture
def actor(inv):
    return actor_de(inv["admin"], date.today())


def test_nombre_unico_sin_mayusculas_y_renombrar(inv, actor):
    taproom = caso_de_uso(uc.GuardarAlmacen).ejecutar(actor, None, " Taproom ")
    assert Almacen.objects.get(pk=taproom).nombre == "Taproom"
    with pytest.raises(AlmacenInvalido, match="Ya existe el almacén principal"):
        caso_de_uso(uc.GuardarAlmacen).ejecutar(actor, None, "principal")
    with pytest.raises(AlmacenInvalido, match="El nombre del almacén es obligatorio"):
        caso_de_uso(uc.GuardarAlmacen).ejecutar(actor, None, " ")
    caso_de_uso(uc.GuardarAlmacen).ejecutar(actor, taproom, "Taproom Miraflores")
    assert Almacen.objects.get(pk=taproom).nombre == "Taproom Miraflores"


def test_almacen_con_stock_no_se_desactiva(inv, actor):
    taproom = caso_de_uso(uc.GuardarAlmacen).ejecutar(actor, None, "Taproom")
    with transaction.atomic():
        linea = Linea(inv["malta"], taproom, D("1"), D("4"))
        inventario().registrar_entrada("SALDO_INICIAL", "AJUSTE", 1, [linea], None, date.today())
    with pytest.raises(AlmacenInvalido, match="El almacén tiene stock"):
        caso_de_uso(uc.CambiarEstadoAlmacen).ejecutar(actor, taproom, False)
    vacio = caso_de_uso(uc.GuardarAlmacen).ejecutar(actor, None, "Cámara fría")
    caso_de_uso(uc.CambiarEstadoAlmacen).ejecutar(actor, vacio, False)
    assert not Almacen.objects.get(pk=vacio).activo


def test_dias_de_alerta_de_vencimiento(inv, actor):
    """0003c, T2, RF-INV-15: sin configurar valen 30; de 1 a 365."""
    from inventory.infrastructure.consultas import dias_alerta

    assert dias_alerta() == 30
    caso = caso_de_uso(uc.GuardarDiasAlerta)
    caso.ejecutar(actor, 45)
    caso.ejecutar(actor, 45)  # guardar dos veces no duplica
    assert dias_alerta() == 45
    for malo in (0, 366):
        with pytest.raises(AlmacenInvalido, match="entre 1 y 365"):
            caso.ejecutar(actor, malo)
