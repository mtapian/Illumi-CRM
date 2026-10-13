"""0002e, T4: impuestos de venta y de compra del producto y su lectura por la fachada
(RF-CAT-56 a 59)."""

from datetime import date
from decimal import Decimal as D

import pytest

from catalog.application import impuestos as ui
from catalog.application import productos as uc
from catalog.domain.errores import ImpuestoInvalido
from catalog.domain.producto import DatosProducto
from catalog.domain.tipos import TipoProducto as T
from catalog.infrastructure.contenedor import (
    caso_de_impuestos,
    caso_de_uso,
    catalogo_query,
    sembrar_impuestos,
)
from catalog.infrastructure.models import Impuesto, ProductoImpuesto
from shared.application.autorizacion import Actor
from shared.domain.errores import AccesoDenegado

pytestmark = pytest.mark.django_db
HOY = date(2026, 10, 12)
IPA = DatosProducto(
    "TER-IPA-330", "IPA", T.BIEN, "UND", se_vende=True, se_compra=False, precio_venta=D("12")
)
MALTA = DatosProducto("INS-MALTA", "Malta", T.BIEN, "KG")


@pytest.fixture
def emp(empresa_catalogo, inventario):
    empresa, actor = empresa_catalogo
    sembrar_impuestos(empresa.id, actor.usuario_id, date(2026, 1, 1))
    return actor


def imp(nombre, tipo="VENTA"):
    return Impuesto.objects.get(nombre=nombre, tipo=tipo).id


def isc(actor, nombre="ISC 330 ml", importe="0.8283", criterio=None):
    id_ = caso_de_impuestos(ui.GuardarImpuesto).ejecutar(
        actor, None, nombre, "VENTA", "ISC", criterio
    )
    caso_de_impuestos(ui.AgregarTasa).ejecutar(actor, id_, D(importe), date(2024, 7, 1))
    return id_


def crear(actor, datos=IPA, venta=None, compra=None):
    return caso_de_uso(uc.CrearProducto).ejecutar(
        actor, datos, impuestos_venta=venta, impuestos_compra=compra
    )


def asignados(producto):
    filas = ProductoImpuesto.objects.filter(producto_id=producto)
    return set(filas.values_list("impuesto__nombre", "impuesto__tipo"))


def test_un_producto_nuevo_trae_igv_en_cada_casilla(emp):
    """RF-CAT-56."""
    p = crear(emp, DatosProducto("X", "X", T.BIEN, "UND", se_vende=True, precio_venta=D("1")))
    assert asignados(p) == {("IGV 18%", "VENTA"), ("IGV 18%", "COMPRA")}
    assert asignados(crear(emp, MALTA)) == {("IGV 18%", "COMPRA")}


def test_listas_invalidas(emp):
    """RF-CAT-57 y 58."""
    i = isc(emp)
    casos = [
        ([i], "El producto debe tener un impuesto de IGV, exonerado o inafecto"),
        ([imp("IGV 18%"), imp("Exonerado")], "El producto debe tener un impuesto de IGV"),
        ([imp("IGV 18%", "COMPRA")], "Un impuesto de compra no va en los impuestos de venta"),
    ]
    for lista, mensaje in casos:
        with pytest.raises(ImpuestoInvalido, match=mensaje):
            crear(emp, venta=lista)
    servicio = DatosProducto(
        "SRV", "Delivery", T.SERVICIO, "SERV", se_vende=True, se_compra=False, precio_venta=D("8")
    )
    with pytest.raises(ImpuestoInvalido, match="Un servicio no lleva ISC"):
        crear(emp, servicio, venta=[imp("IGV 18%"), i])


def test_impuesto_inactivo_no_se_asigna_pero_se_conserva(emp):
    """RF-CAT-55: inactivo no se ofrece en productos nuevos; quien lo tiene lo conserva."""
    exo = imp("Exonerado")
    p = crear(emp, venta=[exo])
    Impuesto.objects.filter(pk=exo).update(activo=False)
    with pytest.raises(ImpuestoInvalido, match="no existe o está inactivo"):
        crear(
            emp, DatosProducto("Y", "Y", T.BIEN, "UND", se_vende=True, precio_venta=D("1")), [exo]
        )
    caso_de_uso(uc.EditarProducto).ejecutar(emp, p, IPA, impuestos_venta=[exo])  # lo conserva


def test_editar_reemplaza_solo_la_lista_enviada(emp):
    p = crear(emp, IPA, venta=[imp("Exonerado")])
    editar = caso_de_uso(uc.EditarProducto)
    editar.ejecutar(emp, p, IPA)  # sin listas: no se tocan
    assert asignados(p) == {("Exonerado", "VENTA")}
    editar.ejecutar(emp, p, IPA, impuestos_venta=[imp("IGV 18%")])
    assert asignados(p) == {("IGV 18%", "VENTA")}


def test_asignar_impuestos_exige_gestionar_impuestos(emp):
    sin_isc = Actor(emp.usuario_id, emp.empresa_id, emp.permisos - {ui.GESTIONAR})
    crear(sin_isc)  # con los de por defecto: válido
    with pytest.raises(AccesoDenegado):
        crear(sin_isc, DatosProducto("Z", "Z", T.BIEN, "UND"), compra=[imp("Exonerado", "COMPRA")])


def test_desglose_por_la_fachada(emp):
    """RF-CAT-59: con los impuestos de venta del producto y sus tasas a la fecha."""
    p = crear(emp, venta=[imp("IGV 18%"), isc(emp)])
    q = catalogo_query()
    d = q.desglose_de_linea(p, D("288.00"), D("24"), HOY)
    assert (d.valor, d.isc, d.igv) == (D("224.19"), D("19.88"), D("43.93"))
    assert q.isc_de_linea(p, D("24"), HOY) == D("19.88")  # lo mismo que con 2.51 × 0.33 L
    porcentual = isc(emp, "ISC 25%", "25", "PORCENTAJE")
    lic = crear(
        emp,
        DatosProducto("LIC", "Pisco", T.BIEN, "UND", se_vende=True, precio_venta=D("100")),
        venta=[imp("IGV 18%"), porcentual],
    )
    d = q.desglose_de_linea(lic, D("100.00"), D("1"), HOY)
    assert (d.valor, d.isc, d.igv) == (D("67.80"), D("16.95"), D("15.25"))
    with pytest.raises(ImpuestoInvalido, match="no tiene tasa vigente al 2024-06-30"):
        q.desglose_de_linea(p, D("12"), D("1"), date(2024, 6, 30))


def test_igv_de_compra_del_producto(emp):
    """RF-CAT-61 (lo usa compras en T5): el % de la afectación de compra a la fecha."""
    exo = crear(emp, MALTA, compra=[imp("Exonerado", "COMPRA")])
    gravado = crear(emp, DatosProducto("INS-LUP", "Lúpulo", T.BIEN, "KG"))
    q = catalogo_query()
    assert q.igv_de_compra(exo, HOY) == ("PORCENTAJE", D("0"))
    assert q.igv_de_compra(gravado, HOY) == ("PORCENTAJE", D("18"))
