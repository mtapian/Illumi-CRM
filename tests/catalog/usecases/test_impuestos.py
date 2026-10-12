"""0002e, T3: maestro de impuestos y sembrador de los seis iniciales (RF-CAT-52 a 55)."""

import io
from datetime import date
from decimal import Decimal as D

import pytest
from django.core.management import call_command

from catalog.application import impuestos as uc
from catalog.domain.errores import ImpuestoInvalido
from catalog.infrastructure.contenedor import caso_de_impuestos, sembrar_impuestos
from catalog.infrastructure.models import Impuesto, ImpuestoTasa, Producto, ProductoImpuesto, Unidad
from shared.application.autorizacion import Actor
from shared.domain.errores import AccesoDenegado

pytestmark = pytest.mark.django_db


def guardar(actor, nombre, tipo="VENTA", codigo="ISC", id_=None):
    return caso_de_impuestos(uc.GuardarImpuesto).ejecutar(actor, id_, nombre, tipo, codigo)


def tasa(actor, impuesto, importe, desde):
    caso_de_impuestos(uc.AgregarTasa).ejecutar(actor, impuesto, D(importe), desde)


def asignar(impuesto_id, activo=True):
    und = Unidad.objects.get(abreviatura="UND")
    p = Producto.objects.create(sku="TER-1", nombre="IPA", unidad=und, activo=activo)
    ProductoImpuesto.objects.create(producto=p, impuesto_id=impuesto_id)
    return p


def test_sembrador_crea_los_seis_impuestos_con_el_igv_vigente(empresa_catalogo):
    """RF-CAT-52: IGV, Exonerado e Inafecto de venta y de compra; IGV desde el registro."""
    empresa, actor = empresa_catalogo
    hoy = date(2026, 10, 12)
    sembrar_impuestos(empresa.id, actor.usuario_id, hoy)
    filas = set(Impuesto.objects.values_list("nombre", "tipo", "codigo"))
    assert filas == {
        (n, t, c)
        for t in ("VENTA", "COMPRA")
        for n, c in (("IGV 18%", "IGV"), ("Exonerado", "EXO"), ("Inafecto", "INA"))
    }
    tasas = ImpuestoTasa.objects.values_list("impuesto__codigo", "vigente_desde", "importe")
    assert sorted(tasas) == sorted(
        [("IGV", hoy, D("18"))] * 2 + [(c, hoy, D("0")) for c in ("EXO", "INA") for _ in "vc"]
    )


def test_nombre_unico_por_tipo_e_isc_solo_de_venta(empresa_catalogo):
    """RF-CAT-53."""
    _, actor = empresa_catalogo
    guardar(actor, "ISC por 750 ml")
    with pytest.raises(ImpuestoInvalido, match="Ya existe el impuesto de venta isc por 750 ml"):
        guardar(actor, "isc por 750 ml")
    guardar(actor, "ISC por 750 ml", "COMPRA", "IGV")  # otro tipo: válido
    with pytest.raises(ImpuestoInvalido, match="El ISC es solo un impuesto de venta"):
        guardar(actor, "ISC compra", "COMPRA", "ISC")
    with pytest.raises(ImpuestoInvalido, match="El nombre del impuesto es obligatorio") as e:
        guardar(actor, "  ")
    assert e.value.campo == "nombre"


def test_tipo_y_codigo_fijos_si_un_producto_lo_usa(empresa_catalogo):
    """RF-CAT-53: el nombre se edita siempre; tipo y código, solo sin uso."""
    _, actor = empresa_catalogo
    isc = guardar(actor, "ISC 330 ml")
    guardar(actor, "ISC 0.33 L", id_=isc)
    asignar(isc)
    with pytest.raises(ImpuestoInvalido, match="su tipo, código y criterio no se pueden cambiar"):
        guardar(actor, "ISC 0.33 L", "VENTA", "IGV", id_=isc)
    assert Impuesto.objects.get(pk=isc).nombre == "ISC 0.33 L"


def test_tasas_por_vigencia(empresa_catalogo):
    """RF-CAT-54: una por fecha, no negativa, 0 en exonerado o inafecto."""
    _, actor = empresa_catalogo
    isc, exo = guardar(actor, "ISC 750 ml"), guardar(actor, "Exonerado", codigo="EXO")
    tasa(actor, isc, "2.01", date(2026, 1, 1))
    tasa(actor, isc, "2.20", date(2027, 1, 1))
    with pytest.raises(ImpuestoInvalido, match="Ya hay una tasa del impuesto en esa fecha"):
        tasa(actor, isc, "2.30", date(2027, 1, 1))
    with pytest.raises(ImpuestoInvalido, match="La tasa no puede ser negativa"):
        tasa(actor, isc, "-1", date(2028, 1, 1))
    with pytest.raises(ImpuestoInvalido, match="Un impuesto exonerado o inafecto tiene tasa 0"):
        tasa(actor, exo, "18", date(2027, 1, 1))
    assert ImpuestoTasa.objects.filter(impuesto_id=isc).count() == 2


def test_no_se_desactiva_si_lo_usan_productos_activos(empresa_catalogo):
    """RF-CAT-55."""
    _, actor = empresa_catalogo
    isc = guardar(actor, "ISC 330 ml")
    producto = asignar(isc)
    estado = caso_de_impuestos(uc.CambiarEstadoImpuesto)
    with pytest.raises(ImpuestoInvalido, match="El impuesto está asignado a productos activos"):
        estado.ejecutar(actor, isc, False)
    Producto.objects.filter(pk=producto.pk).update(activo=False)
    estado.ejecutar(actor, isc, False)
    assert not Impuesto.objects.get(pk=isc).activo


def test_exige_gestionar_impuestos(empresa_catalogo):
    empresa, _ = empresa_catalogo
    sin_permiso = Actor(usuario_id=1, empresa_id=empresa.id, permisos=frozenset())
    with pytest.raises(AccesoDenegado):
        guardar(sin_permiso, "ISC 330 ml")


def test_comando_siembra_solo_empresas_sin_impuestos(empresa_catalogo):
    """Puente hasta T6: las empresas existentes reciben sus seis impuestos una sola vez."""
    empresa, _ = empresa_catalogo
    call_command("sembrar_impuestos", stdout=io.StringIO())
    call_command("sembrar_impuestos", stdout=io.StringIO())
    assert Impuesto.all_tenants.filter(empresa=empresa).count() == 6


def test_criterio_elegido_y_fijo_con_uso(empresa_catalogo):
    """Enmienda 1: por defecto % en IGV/EXO/INA y fijo en ISC; el usuario puede cambiarlo
    mientras ningún producto lo use."""
    _, actor = empresa_catalogo
    caso = caso_de_impuestos(uc.GuardarImpuesto)
    isc = guardar(actor, "ISC 25%")
    assert Impuesto.objects.get(pk=isc).criterio == "FIJO"
    caso.ejecutar(actor, isc, "ISC 25%", "VENTA", "ISC", "PORCENTAJE")
    assert Impuesto.objects.get(pk=isc).criterio == "PORCENTAJE"
    asignar(isc)
    with pytest.raises(ImpuestoInvalido, match="no se pueden cambiar"):
        caso.ejecutar(actor, isc, "ISC 25%", "VENTA", "ISC", "FIJO")
    igv = caso.ejecutar(actor, None, "IGV fijo", "VENTA", "IGV", "FIJO")
    assert Impuesto.objects.get(pk=igv).criterio == "FIJO"
