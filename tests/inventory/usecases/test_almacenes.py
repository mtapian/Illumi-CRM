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
from shared.domain.accesos import CATALOGO
from tenancy.infrastructure.contenedor import actor_de
from tenancy.infrastructure.models import PlanFuncionalidad

pytestmark = pytest.mark.django_db


@pytest.fixture
def actor(inv):
    for f in CATALOGO:
        PlanFuncionalidad.objects.create(plan=inv["empresa"].plan, funcionalidad_id=f)
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
