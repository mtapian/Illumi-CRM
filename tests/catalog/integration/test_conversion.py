"""0002a enmienda 4, T32, T36 y T38: conversión de los datos existentes (RF-CAT-44, 48).

Migra el catálogo hasta antes de la enmienda, crea datos con el modelo viejo y migra hasta el
final: tipos → casillas, presentación → receta, categoría de ISC → tasas en el producto.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

ANTES = [("catalog", "0006_marcas")]
ISC_POR_LITRO = [("catalog", "0011_criterio_del_impuesto")]


def _migrar(destino=None):
    """Sin destino migra hasta la última: la base queda como la esperan los demás tests."""
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    destino = destino or executor.loader.graph.leaf_nodes()
    executor.migrate(destino)
    return executor.loader.project_state(destino).apps


@pytest.mark.django_db(transaction=True)
def test_convierte_tipos_presentaciones_y_categorias_de_isc(crear_empresa):
    empresa = crear_empresa()
    apps = _migrar(ANTES)
    Unidad, Producto = apps.get_model("catalog", "Unidad"), apps.get_model("catalog", "Producto")
    und = Unidad.objects.create(
        empresa_id=empresa.id, nombre="U", abreviatura="UND", codigo_sunat="NIU"
    )
    litro = Unidad.objects.create(
        empresa_id=empresa.id, nombre="L", abreviatura="L", codigo_sunat="LTR"
    )
    categoria = apps.get_model("catalog", "IscCategoria").objects.create(
        empresa_id=empresa.id, nombre="Cerveza", codigo_tipo_sistema="02"
    )
    tarifas = apps.get_model("catalog", "IscTarifa").objects
    tarifas.create(
        categoria=categoria, vigente_desde=date(2024, 7, 1), monto_por_litro=Decimal("2.51")
    )
    tarifas.create(
        categoria=categoria, vigente_desde=date(2027, 1, 1), monto_por_litro=Decimal("2.70")
    )

    def crear(sku, tipo, u=und, **kw):
        return Producto.objects.create(
            empresa_id=empresa.id, sku=sku, nombre=sku, tipo=tipo, unidad=u, **kw
        )

    crear("INS-MALTA", "INSUMO")
    botella = crear("ENV-BOT", "ENVASE")
    granel = crear("GRA-IPA", "GRANEL", litro, controla_lote=True, prefijo_lote="IPA")
    crear("MER-AGUA", "MERCADERIA", precio_venta=3)
    ipa = crear(
        "TER-IPA",
        "TERMINADO",
        precio_venta=12,
        vida_util_dias=120,
        controla_lote=True,
        isc_categoria=categoria,
    )
    presentacion = apps.get_model("catalog", "Presentacion").objects.create(
        empresa_id=empresa.id, producto=ipa, granel=granel, contenido_litros=Decimal("0.33")
    )
    apps.get_model("catalog", "PresentacionMaterial").objects.create(
        presentacion=presentacion, material=botella, cantidad_por_unidad=1
    )

    apps = _migrar(ISC_POR_LITRO)
    Producto = apps.get_model("catalog", "Producto")
    casillas = {
        p.sku: (p.tipo, p.se_vende, p.se_compra, p.se_fabrica) for p in Producto.objects.all()
    }
    assert casillas == {
        "INS-MALTA": ("BIEN", False, True, False),
        "ENV-BOT": ("BIEN", False, True, False),
        "GRA-IPA": ("BIEN", False, False, True),
        "MER-AGUA": ("BIEN", True, True, False),
        "TER-IPA": ("BIEN", True, False, True),
    }
    receta = apps.get_model("catalog", "RecetaComponente").objects.filter(producto_id=ipa.id)
    assert {(r.componente_id, r.cantidad_por_unidad) for r in receta} == {
        (granel.id, Decimal("0.3300")),
        (botella.id, Decimal("1.0000")),
    }
    ter = Producto.objects.get(sku="TER-IPA")
    assert (ter.isc_sistema, ter.isc_codigo_tipo_sistema, ter.contenido_litros) == (
        "ESPECIFICO",
        "02",
        Decimal("0.3300"),
    )
    tasas = apps.get_model("catalog", "ProductoIscTasa").objects.filter(producto_id=ipa.id)
    assert sorted(tasas.values_list("vigente_desde", "monto_por_litro")) == [
        (date(2024, 7, 1), Decimal("2.5100")),
        (date(2027, 1, 1), Decimal("2.7000")),
    ]
    _migrar()


@pytest.mark.django_db(transaction=True)
def test_convierte_igv_e_isc_por_litro_a_impuestos(crear_empresa):
    """0002e, RF-CAT-60: IGV con su historial en los dos "IGV 18%"; ISC por litro → monto
    fijo por unidad compartido por historial; tolera una empresa ya sembrada; reversible."""
    andina, altaria = crear_empresa(), crear_empresa(ruc="20100066603", razon_social="Altaria")
    apps = _migrar(ISC_POR_LITRO)
    Parametro = apps.get_model("tenancy", "ParametroVigencia")
    Parametro.objects.get_or_create(
        empresa=None, clave="igv_pct", vigente_desde=date(2011, 3, 1), defaults={"valor": 18}
    )
    Parametro.objects.create(
        empresa_id=andina.id, clave="igv_pct", vigente_desde=date(2027, 1, 1), valor=16
    )
    Impuesto, Tasa = (
        apps.get_model("catalog", "Impuesto"),
        apps.get_model("catalog", "ImpuestoTasa"),
    )
    sembrado = Impuesto.all_tenants.create(  # Altaria ya pasó por `sembrar_impuestos`
        empresa_id=altaria.id, nombre="IGV 18%", tipo="VENTA", codigo="IGV"
    )
    Tasa.all_tenants.create(
        empresa_id=altaria.id, impuesto=sembrado, vigente_desde=date(2026, 10, 1), importe=18
    )
    Unidad, Producto = apps.get_model("catalog", "Unidad"), apps.get_model("catalog", "Producto")
    Asignado = apps.get_model("catalog", "ProductoImpuesto")
    IscTasa = apps.get_model("catalog", "ProductoIscTasa")

    def crear(empresa, sku, litros=None, tasas=(), **kw):
        und = Unidad.all_tenants.get_or_create(
            empresa_id=empresa.id,
            abreviatura="UND",
            defaults={"nombre": "U", "codigo_sunat": "NIU"},
        )[0]
        isc = {"isc_sistema": "ESPECIFICO", "isc_codigo_tipo_sistema": "02"} if tasas else {}
        p = Producto.all_tenants.create(
            empresa_id=empresa.id,
            sku=sku,
            nombre=sku,
            unidad=und,
            contenido_litros=litros,
            **isc,
            **kw,
        )
        for desde, monto in tasas:
            IscTasa.all_tenants.create(
                empresa_id=empresa.id, producto_id=p.pk, vigente_desde=desde, monto_por_litro=monto
            )
        return p

    tasas = [(date(2024, 7, 1), Decimal("2.51")), (date(2027, 1, 1), Decimal("2.70"))]
    vende = {"se_vende": True, "se_compra": False, "precio_venta": 12}
    crear(andina, "IPA", Decimal("0.33"), tasas, se_fabrica=True, **vende)
    crear(andina, "PALE", Decimal("0.33"), tasas, **vende)
    crear(andina, "CAJA", Decimal("3.96"), tasas, **vende)
    crear(andina, "MALTA")
    ya = crear(altaria, "ALBA", Decimal("0.33"), tasas[:1], **vende)
    Asignado.all_tenants.create(empresa_id=altaria.id, producto=ya, impuesto=sembrado)

    apps = _migrar()
    Impuesto, Tasa = (
        apps.get_model("catalog", "Impuesto"),
        apps.get_model("catalog", "ImpuestoTasa"),
    )
    Asignado = apps.get_model("catalog", "ProductoImpuesto")

    def tasas_de(empresa, nombre, tipo="VENTA"):
        imp = Impuesto.all_tenants.get(empresa_id=empresa.id, nombre=nombre, tipo=tipo)
        return sorted(Tasa.all_tenants.filter(impuesto=imp).values_list("vigente_desde", "importe"))

    def impuestos_de(empresa, sku):
        filas = Asignado.all_tenants.filter(empresa_id=empresa.id, producto__sku=sku)
        return set(filas.values_list("impuesto__nombre", "impuesto__tipo"))

    igv = [(date(2011, 3, 1), Decimal("18.0000")), (date(2027, 1, 1), Decimal("16.0000"))]
    assert tasas_de(andina, "IGV 18%") == tasas_de(andina, "IGV 18%", "COMPRA") == igv
    assert tasas_de(andina, "Exonerado", "COMPRA") == [(date(2011, 3, 1), Decimal("0.0000"))]
    assert tasas_de(andina, "ISC 0.33 L") == [
        (date(2024, 7, 1), Decimal("0.8283")),
        (date(2027, 1, 1), Decimal("0.8910")),
    ]
    assert tasas_de(andina, "ISC 3.96 L")[0] == (date(2024, 7, 1), Decimal("9.9396"))
    assert (
        impuestos_de(andina, "IPA")
        == impuestos_de(andina, "PALE")
        == {
            ("IGV 18%", "VENTA"),
            ("ISC 0.33 L", "VENTA"),
        }
    )
    assert impuestos_de(andina, "MALTA") == {("IGV 18%", "COMPRA")}
    # Altaria: el IGV sembrado se completa con la historia; su ISC tiene otro historial.
    assert Impuesto.all_tenants.filter(empresa_id=altaria.id).count() == 7
    assert tasas_de(altaria, "IGV 18%") == [
        (date(2011, 3, 1), Decimal("18.0000")),
        (date(2026, 10, 1), Decimal("18.0000")),
    ]
    assert impuestos_de(altaria, "ALBA") == {("IGV 18%", "VENTA"), ("ISC 0.33 L", "VENTA")}
    assert tasas_de(altaria, "ISC 0.33 L") == [(date(2024, 7, 1), Decimal("0.8283"))]

    apps = _migrar(ISC_POR_LITRO)  # reversible: vuelve el ISC por litro
    Producto = apps.get_model("catalog", "Producto")
    IscTasa = apps.get_model("catalog", "ProductoIscTasa")
    ipa = Producto.all_tenants.get(empresa_id=andina.id, sku="IPA")
    assert (ipa.isc_sistema, ipa.isc_codigo_tipo_sistema) == ("ESPECIFICO", "02")
    restauradas = IscTasa.all_tenants.filter(producto_id=ipa.pk)
    assert sorted(restauradas.values_list("vigente_desde", "monto_por_litro")) == tasas
    _migrar()
