from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from django.db import migrations

CUATRO = Decimal("0.0001")
INICIALES = [("IGV 18%", "IGV"), ("Exonerado", "EXO"), ("Inafecto", "INA")]


def _historial_igv(Parametro, empresa_id):
    """El IGV que veía la empresa en cada fecha: el propio si tiene uno vigente, si no el de
    la plataforma (como `TenancyService.parametro_vigente`), sin repetir valores seguidos."""
    filas = Parametro.objects.filter(clave="igv_pct").order_by("vigente_desde")
    propias = [(f.vigente_desde, f.valor) for f in filas if f.empresa_id == empresa_id]
    plataforma = [(f.vigente_desde, f.valor) for f in filas if f.empresa_id is None]
    historial = []
    for fecha in sorted({d for d, _ in propias + plataforma}):
        vigentes = [v for d, v in propias if d <= fecha] or [v for d, v in plataforma if d <= fecha]
        if vigentes and (not historial or historial[-1][1] != vigentes[-1]):
            historial.append((fecha, vigentes[-1]))
    return historial


def _nombre_libre(nombre, usados):
    candidato, n = nombre, 1
    while candidato.lower() in usados:
        n += 1
        candidato = f"{nombre} ({n})"
    usados.add(candidato.lower())
    return candidato


def convertir(apps, schema_editor):
    """0002e, RF-CAT-60: IGV de la empresa → tasas de sus dos "IGV 18%"; ISC por litro →
    ISC de venta de monto fijo por unidad, compartido por los productos con el mismo
    historial; cada producto con "IGV 18%" en cada casilla marcada. Tolera empresas ya
    sembradas (comando `sembrar_impuestos`) y productos que ya tienen impuestos."""
    Empresa = apps.get_model("tenancy", "Empresa")
    Parametro = apps.get_model("tenancy", "ParametroVigencia")
    Impuesto = apps.get_model("catalog", "Impuesto")
    Tasa = apps.get_model("catalog", "ImpuestoTasa")
    Producto = apps.get_model("catalog", "Producto")
    ProductoImpuesto = apps.get_model("catalog", "ProductoImpuesto")
    ProductoIscTasa = apps.get_model("catalog", "ProductoIscTasa")
    for empresa_id in Empresa.objects.values_list("id", flat=True):
        impuestos = Impuesto.all_tenants.filter(empresa_id=empresa_id)
        historial_igv = _historial_igv(Parametro, empresa_id)
        igv = {}
        for tipo in ("VENTA", "COMPRA"):
            for nombre, codigo in INICIALES:
                imp = impuestos.filter(tipo=tipo, codigo=codigo).order_by("id").first()
                if imp is None:
                    imp = Impuesto.all_tenants.create(
                        empresa_id=empresa_id, nombre=nombre, tipo=tipo, codigo=codigo
                    )
                historial = historial_igv if codigo == "IGV" else historial_igv[:1]
                fechas = set(
                    Tasa.all_tenants.filter(impuesto=imp).values_list("vigente_desde", flat=True)
                )
                for desde, valor in historial:
                    if desde not in fechas:
                        Tasa.all_tenants.create(
                            empresa_id=empresa_id,
                            impuesto=imp,
                            vigente_desde=desde,
                            importe=valor if codigo == "IGV" else 0,
                        )
                if codigo == "IGV":
                    igv[tipo] = imp

        grupos = defaultdict(list)
        for p in Producto.all_tenants.filter(empresa_id=empresa_id, isc_sistema__isnull=False):
            tasas = ProductoIscTasa.all_tenants.filter(producto_id=p.pk).order_by("vigente_desde")
            historial = tuple(
                (
                    t.vigente_desde,
                    (t.monto_por_litro * p.contenido_litros).quantize(CUATRO, ROUND_HALF_UP),
                )
                for t in tasas
            )
            if historial:
                grupos[historial].append(p)
        usados = {
            n.lower() for n in impuestos.filter(tipo="VENTA").values_list("nombre", flat=True)
        }
        isc_de = {}
        for historial, productos in grupos.items():
            litros = format(productos[0].contenido_litros.normalize(), "f")
            imp = Impuesto.all_tenants.create(
                empresa_id=empresa_id,
                nombre=_nombre_libre(f"ISC {litros} L", usados),
                tipo="VENTA",
                codigo="ISC",
                criterio="FIJO",
            )
            Tasa.all_tenants.bulk_create(
                Tasa(empresa_id=empresa_id, impuesto=imp, vigente_desde=d, importe=v)
                for d, v in historial
            )
            isc_de.update({p.pk: imp for p in productos})

        for p in Producto.all_tenants.filter(empresa_id=empresa_id):
            tiene = set(
                ProductoImpuesto.all_tenants.filter(producto=p).values_list(
                    "impuesto__tipo", "impuesto__codigo"
                )
            )
            nuevos = []
            if p.se_vende and not any(t == "VENTA" for t, _ in tiene):
                nuevos.append(igv["VENTA"])
            if p.se_compra and not any(t == "COMPRA" for t, _ in tiene):
                nuevos.append(igv["COMPRA"])
            if p.pk in isc_de and ("VENTA", "ISC") not in tiene:
                nuevos.append(isc_de[p.pk])
            ProductoImpuesto.all_tenants.bulk_create(
                ProductoImpuesto(empresa_id=empresa_id, producto=p, impuesto=i) for i in nuevos
            )
    # Como en 0008: las FK diferidas se verifican ya para poder alterar las tablas después.
    schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")


def revertir(apps, schema_editor):
    """Vuelve al ISC por litro: cada producto con un ISC fijo y litros recibe sus tasas
    (importe ÷ litros). Los impuestos se conservan: existían desde 0010."""
    Producto = apps.get_model("catalog", "Producto")
    ProductoImpuesto = apps.get_model("catalog", "ProductoImpuesto")
    Tasa = apps.get_model("catalog", "ImpuestoTasa")
    ProductoIscTasa = apps.get_model("catalog", "ProductoIscTasa")
    asignados = ProductoImpuesto.all_tenants.filter(
        impuesto__codigo="ISC", impuesto__criterio="FIJO", producto__contenido_litros__gt=0
    ).select_related("producto")
    for a in asignados:
        p = a.producto
        Producto.all_tenants.filter(pk=p.pk).update(
            isc_sistema="ESPECIFICO", isc_codigo_tipo_sistema="02"
        )
        ProductoIscTasa.all_tenants.bulk_create(
            ProductoIscTasa(
                empresa_id=p.empresa_id,
                producto_id=p.pk,
                vigente_desde=t.vigente_desde,
                monto_por_litro=(t.importe / p.contenido_litros).quantize(CUATRO, ROUND_HALF_UP),
            )
            for t in Tasa.all_tenants.filter(impuesto_id=a.impuesto_id, importe__gt=0)
        )
    schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0011_criterio_del_impuesto"),
        ("tenancy", "0009_auditoria_inmutable"),
    ]

    operations = [
        migrations.RunPython(convertir, revertir),
        migrations.RunSQL(
            "DROP TRIGGER IF EXISTS trg_producto_isc_tasa_inmutable ON catalog_productoisctasa;",
            "CREATE TRIGGER trg_producto_isc_tasa_inmutable BEFORE UPDATE OR DELETE"
            " ON catalog_productoisctasa FOR EACH ROW EXECUTE FUNCTION fn_rechazar_cambio();",
        ),
        migrations.RemoveConstraint(model_name="producto", name="isc_solo_bien_vendible_por_litro"),
        migrations.RemoveField(model_name="producto", name="isc_sistema"),
        migrations.RemoveField(model_name="producto", name="isc_codigo_tipo_sistema"),
        migrations.DeleteModel(name="ProductoIscTasa"),
    ]
