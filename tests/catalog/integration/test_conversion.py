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

    apps = _migrar()
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
