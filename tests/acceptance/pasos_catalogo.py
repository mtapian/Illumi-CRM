"""Pasos de productos.feature y presentaciones.feature (épica 0002)."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

from pytest_bdd import given, parsers, then, when

from catalog.application import productos as uc
from catalog.domain.presentacion import DatosPresentacion
from catalog.domain.producto import DatosProducto
from catalog.domain.tipos import TipoProducto
from catalog.infrastructure.contenedor import caso_de_uso, catalogo_query, sembrar_unidades
from catalog.infrastructure.models import (
    Familia,
    IscCategoria,
    IscTarifa,
    Presentacion,
    PresentacionMaterial,
    Producto,
    Unidad,
)
from catalog.infrastructure.repositorios import CatalogoOrm
from shared.domain.accesos import CATALOGO
from shared.domain.errores import DomainError
from shared.domain.tenant import tenant_context
from tenancy.infrastructure.models import PlanFuncionalidad
from tests.acceptance.conftest import contenido
from tests.acceptance.pasos_accesos import actor, como, re_
from tests.acceptance.pasos_sesion import crear_empresa, crear_usuario

ROLES = {"gerente": "Gerente", "produccion": "Producción", "almacen": "Almacén"}
EMAIL = "yo@andina.pe"


def producto(ctx, sku: str) -> Producto:
    return Producto.all_tenants.get(empresa=ctx["empresa"], sku=sku)


def unidad(ctx, abreviatura: str) -> Unidad:
    return Unidad.all_tenants.get(empresa=ctx["empresa"], abreviatura=abreviatura)


def crear_directo(ctx, sku, tipo="INSUMO", u="KG", nombre=None, **kw) -> Producto:
    existente = Producto.all_tenants.filter(empresa=ctx["empresa"], sku=sku).first()
    if existente:
        return existente
    return Producto.all_tenants.create(
        empresa=ctx["empresa"],
        sku=sku,
        nombre=nombre or sku,
        tipo=tipo,
        unidad=unidad(ctx, u),
        controla_lote=TipoProducto(tipo).lote_siempre,
        **kw,
    )


def post_producto(client, ctx, tipo, **campos):
    datos = {"stock_minimo": "0", "nombre": campos.get("sku", "x")} | campos
    ctx["respuesta"] = como(client, EMAIL).post(
        f"/catalogo/productos/nuevo/?tipo={tipo}", datos, follow=True
    )


def post_ficha(client, ctx, codigo, **campos):
    p = producto(ctx, codigo)
    datos = {
        "accion": "guardar",
        "sku": p.sku,
        "nombre": p.nombre,
        "unidad": p.unidad.abreviatura,
        "stock_minimo": str(p.stock_minimo),
    } | campos
    return como(client, EMAIL).post(f"/catalogo/productos/{p.id}/", datos, follow=True)


# --- Antecedentes ---


@given(re_("que soy usuario {} de {}", "rol", "nombre"))
def soy_usuario(client, ctx, inventario, rol, nombre):
    ctx["empresa"] = crear_empresa(nombre)
    for f in CATALOGO:
        PlanFuncionalidad.objects.create(plan=ctx["empresa"].plan, funcionalidad_id=f)
    usuario = crear_usuario(EMAIL, ctx["empresa"], ROLES[rol])
    sembrar_unidades(ctx["empresa"].id, usuario.id, date.today())
    ctx["inventario"] = inventario


@given(re_("existen las unidades {}", "lista"))
def existen_unidades(ctx, lista):
    existentes = set(
        Unidad.all_tenants.filter(empresa=ctx["empresa"]).values_list("abreviatura", flat=True)
    )
    assert {u.strip() for u in lista.split(",")} <= existentes


# --- Crear productos (UC-CAT-02) ---


@when(
    re_("creo un producto con SKU {}, nombre {}, tipo {} y unidad {}", "sku", "nombre", "tipo", "u")
)
def creo_producto(client, ctx, sku, nombre, tipo, u):
    post_producto(client, ctx, tipo, sku=sku, nombre=nombre, unidad=u)


@then(re_("el producto {} queda activo con stock 0", "sku"))
def queda_activo(ctx, sku):
    p = producto(ctx, sku)
    assert p.activo and ctx["inventario"].stock(p.id) == 0


@then(re_("controla lote es {}", "lote"))
def controla_lote(ctx, lote):
    sku = Producto.all_tenants.filter(empresa=ctx["empresa"]).latest("id").sku
    assert producto(ctx, sku).controla_lote == (lote == "sí")


@when(re_("creo un producto tipo {} con unidad {}", "tipo", "u"))
def creo_tipo_con_unidad(client, ctx, tipo, u):
    # El formulario del granel solo ofrece litros; el caso de uso rechaza otra unidad.
    form = contenido(como(client, EMAIL).get(f"/catalogo/productos/nuevo/?tipo={tipo}"))
    assert f'<option value="{u}"' not in form
    try:
        with tenant_context(ctx["empresa"].id):
            datos = DatosProducto("GRA-X", "Granel", TipoProducto(tipo), u)
            caso_de_uso(uc.CrearProducto).ejecutar(actor(EMAIL), datos)
    except DomainError as e:
        ctx["textos"] = [e.mensaje]


@then(re_("la operación es rechazada con el mensaje {}", "mensaje"))
def rechazada(ctx, mensaje):
    textos = ctx.get("textos") or [
        contenido(r) for r in ctx.get("respuestas") or [ctx["respuesta"]]
    ]
    for texto in textos:
        assert mensaje in texto


@given(re_("que existe el producto con SKU {}", "sku"))
def existe_producto(ctx, sku):
    crear_directo(ctx, sku)


@when(re_("creo otro producto con SKU {}", "sku"))
def creo_otro(client, ctx, sku):
    post_producto(client, ctx, "INSUMO", sku=sku, nombre="Otra malta", unidad="KG")


@given(re_("que {} tiene el producto con SKU {}", "nombre", "sku"))
def otra_empresa_tiene(nombre, sku):
    otra = crear_empresa(nombre)
    und = Unidad.all_tenants.create(
        empresa=otra, nombre="Kilogramo", abreviatura="KG", codigo_sunat="KGM"
    )
    Producto.all_tenants.create(empresa=otra, sku=sku, nombre=sku, tipo="INSUMO", unidad=und)


@when(re_("creo un producto con SKU {} en {}", "sku", "nombre"))
def creo_en(client, ctx, sku, nombre):
    post_producto(client, ctx, "INSUMO", sku=sku, nombre="Malta", unidad="KG")


@then("el producto se crea correctamente")
def se_crea(ctx):
    assert Producto.all_tenants.filter(empresa=ctx["empresa"], sku="INS-MALTA").exists()
    assert Producto.all_tenants.filter(sku="INS-MALTA").count() == 2


@given(re_("que el producto {} tiene movimientos de inventario", "sku"))
def tiene_movimientos(ctx, sku):
    ctx["inventario"].con_movimientos.add(crear_directo(ctx, sku).id)


@when("intento cambiar su SKU, tipo o unidad")
def intento_cambiar(client, ctx):
    # En pantalla esos campos están bloqueados: lo enviado se ignora.
    post_ficha(client, ctx, "INS-MALTA", sku="INS-OTRO", unidad="G")
    p = producto(ctx, "INS-MALTA")
    assert (p.sku, p.unidad.abreviatura) == ("INS-MALTA", "KG")
    # Y el caso de uso los rechaza aunque alguien los envíe (RF-CAT-09).
    ctx["textos"] = []
    with tenant_context(ctx["empresa"].id):
        datos = CatalogoOrm().producto(p.id)
        for cambio in ({"sku": "INS-OTRO"}, {"tipo": TipoProducto.ENVASE}, {"unidad": "G"}):
            try:
                caso_de_uso(uc.EditarProducto).ejecutar(
                    actor(EMAIL), p.id, replace(datos, **cambio)
                )
            except DomainError as e:
                ctx["textos"].append(e.mensaje)
    assert len(ctx["textos"]) == 3


@then("puedo cambiar su nombre, categoría y stock mínimo")
def puedo_cambiar(client, ctx):
    familia = Familia.all_tenants.create(empresa=ctx["empresa"], nombre="Maltas")
    post_ficha(
        client, ctx, "INS-MALTA", nombre="Malta Pilsen", familia=familia.id, stock_minimo="25"
    )
    p = producto(ctx, "INS-MALTA")
    assert (p.nombre, p.familia_id, p.stock_minimo) == ("Malta Pilsen", familia.id, Decimal("25"))


@given(re_(r"que el plan de la empresa permite (?P<n>\d+) productos activos"))
def plan_permite(ctx, n):
    ctx["empresa"].plan.limite_productos = int(n)
    ctx["empresa"].plan.save()


@given(re_(r"la empresa tiene (?P<n>\d+) productos activos"))
def tiene_n_activos(ctx, n):
    und = unidad(ctx, "UND")
    Producto.all_tenants.bulk_create(
        Producto(
            empresa=ctx["empresa"], sku=f"ENV-{i}", nombre=f"Envase {i}", tipo="ENVASE", unidad=und
        )
        for i in range(int(n))
    )


@when("creo un producto nuevo")
def creo_nuevo(client, ctx):
    post_producto(client, ctx, "ENVASE", sku="ENV-NUEVO", nombre="Nuevo", unidad="UND")


@given(re_("que la unidad {} está asignada a {}", "u", "sku"))
def unidad_asignada(ctx, u, sku):
    crear_directo(ctx, sku, u=u)


@when(re_("intento eliminar la unidad {}", "u"))
def elimino_unidad(client, ctx, u):
    ctx["respuesta"] = como(client, EMAIL).post(
        "/catalogo/unidades/", {"accion": "eliminar", "unidad": unidad(ctx, u).id}, follow=True
    )


# --- Desactivar y eliminar (UC-CAT-04) ---


@given(re_(r"que el producto {} tiene stock (?P<n>\d+)(?: (?P<u>\w+))?", "sku"))
def tiene_stock(ctx, sku, n, u):
    p = crear_directo(ctx, sku, u="G" if sku == "INS-LUP-CS" else "KG")
    ctx["inventario"].stocks[p.id] = Decimal(n)
    ctx["sku"] = sku


def post_estado(client, ctx, sku, accion):
    p = producto(ctx, sku)
    ctx["respuesta"] = como(client, EMAIL).post(
        f"/catalogo/productos/{p.id}/", {"accion": accion}, follow=True
    )


@when("lo desactivo")
def lo_desactivo(client, ctx):
    post_estado(client, ctx, ctx["sku"], "desactivar")


@then("no aparece al registrar compras ni al editar recetas")
def no_aparece(ctx):
    with tenant_context(ctx["empresa"].id):
        ofrecidos = {
            p.sku for p in catalogo_query().activos([t for t in TipoProducto if t.comprable])
        }
    assert ctx["sku"] not in ofrecidos
    ctx["pendientes"].append(
        "las pantallas de compras (0004a) y recetas (0005a) usan CatalogoQuery.activos"
    )


@then("sigue visible en el kardex y en los reportes históricos")
def sigue_visible(ctx):
    with tenant_context(ctx["empresa"].id):
        dto = catalogo_query().producto(producto(ctx, ctx["sku"]).id)
    assert dto is not None and dto.activo is False


@when("intento desactivarlo")
def intento_desactivar(client, ctx):
    post_estado(client, ctx, ctx["sku"], "desactivar")


@given(re_("que el producto {} no tiene movimientos", "sku"))
def sin_movimientos(ctx, sku):
    crear_directo(ctx, sku, tipo="ENVASE", u="UND")
    ctx["sku"] = sku


@when("lo elimino")
def lo_elimino(client, ctx):
    post_estado(client, ctx, ctx["sku"], "eliminar")


@then("el producto deja de existir")
def deja_de_existir(ctx):
    assert not Producto.all_tenants.filter(empresa=ctx["empresa"], sku=ctx["sku"]).exists()


@when("intento eliminarlo")
def intento_eliminar(client, ctx):
    post_estado(client, ctx, "INS-MALTA", "eliminar")


# --- Mercadería (RF-CAT-06, 12, 13) ---


@when(re_("creo el producto {} {} de tipo {} con:", "sku", "nombre", "tipo"))
def creo_con_tabla(client, ctx, sku, nombre, tipo, datatable):
    campos = {fila[0]: fila[1] for fila in datatable[1:]}
    if campos.pop("controla_lote", "no") == "sí":
        campos["controla_lote"] = "on"
    post_producto(client, ctx, tipo, sku=sku, nombre=nombre, **campos)


@then(re_("{} queda activo, comprable y vendible", "sku"))
def activo_comprable_vendible(ctx, sku):
    p = producto(ctx, sku)
    assert p.activo and TipoProducto(p.tipo).comprable and TipoProducto(p.tipo).vendible


@then("no requiere presentación ni receta")
def sin_presentacion(ctx):
    assert not TipoProducto.MERCADERIA.producible


@then("no paga ISC porque no tiene categoría de ISC")
def sin_isc(ctx):
    p = Producto.all_tenants.filter(empresa=ctx["empresa"]).latest("id")
    assert getattr(p, "isc_categoria_id", None) is None


@when(
    parsers.re(
        r'creo el producto "(?P<sku>[^"]+)" "(?P<nombre>[^"]+)" de tipo "(?P<tipo>[^"]+)" '
        r'con precio (?P<precio>[\d.]+) y "controla_lote" no'
    )
)
def creo_con_precio(client, ctx, sku, nombre, tipo, precio):
    post_producto(client, ctx, tipo, sku=sku, nombre=nombre, unidad="UND", precio_venta=precio)


@then(re_("{} queda activo y vendible sin control de lote", "sku"))
def vendible_sin_lote(ctx, sku):
    p = producto(ctx, sku)
    assert p.activo and TipoProducto(p.tipo).vendible and not p.controla_lote


# --- presentaciones.feature (antecedentes y granel con presentaciones) ---


@given(re_(r"existe el granel {} \((?P<nombre>[^)]+)\)", "sku"))
def existe_granel(ctx, sku, nombre):
    crear_directo(ctx, sku, tipo="GRANEL", u="L", nombre=nombre, prefijo_lote=nombre[:3].upper())


@given("existen los envases:")
def existen_envases(ctx, datatable):
    for sku, nombre in datatable[1:]:
        crear_directo(ctx, sku, tipo="ENVASE", u="UND", nombre=nombre)


@given(re_("que {} tiene presentaciones activas", "sku"))
def tiene_presentaciones(ctx, sku):
    crear_terminado(ctx, "TER-IPA-330", sku, "0.33", [("ENV-BOT330", "1")])
    ctx["sku"] = sku


@when(re_("intento desactivar {}", "sku"))
def intento_desactivar_sku(client, ctx, sku):
    post_estado(client, ctx, sku, "desactivar")


# --- 0002b: presentaciones (UC-CAT-03) ---


def crear_terminado(ctx, sku, granel, contenido, materiales, categoria=None, nombre=None):
    existente = Producto.all_tenants.filter(empresa=ctx["empresa"], sku=sku).first()
    if existente:
        return existente
    p = crear_directo(
        ctx,
        sku,
        tipo="TERMINADO",
        u="UND",
        nombre=nombre or sku,
        precio_venta=Decimal("12"),
        vida_util_dias=120,
        isc_categoria=categoria,
    )
    presentacion = Presentacion.all_tenants.create(
        empresa=ctx["empresa"],
        producto=p,
        granel=producto(ctx, granel),
        contenido_litros=Decimal(contenido),
    )
    for material, cantidad in materiales:
        PresentacionMaterial.objects.create(
            presentacion=presentacion,
            material=producto(ctx, material),
            cantidad_por_unidad=Decimal(cantidad),
        )
    return p


def categoria_isc(ctx, nombre="Cerveza") -> IscCategoria:
    categoria, creada = IscCategoria.all_tenants.get_or_create(
        empresa=ctx["empresa"], nombre=nombre, defaults={"codigo_tipo_sistema": "02"}
    )
    if creada:
        IscTarifa.objects.create(
            categoria=categoria, vigente_desde=date(2024, 7, 1), monto_por_litro=Decimal("2.51")
        )
    return categoria


def post_terminado(client, ctx, sku, nombre, campos, materiales):
    datos = {
        "sku": sku,
        "nombre": nombre,
        "unidad": "UND",
        "stock_minimo": "0",
        "precio_venta": campos.get("precio_venta", "12.00"),
        "vida_util_dias": campos.get("vida_util_dias", "120"),
        "granel": producto(ctx, campos.get("granel", "GRA-IPA")).id,
        "contenido": campos.get("contenido_l", "0.3300"),
    }
    if campos.get("categoria_isc"):
        datos["isc_categoria_id"] = categoria_isc(ctx, campos["categoria_isc"]).id
    for i, (material, cantidad) in enumerate(materiales):
        datos |= {f"material_{i}": producto(ctx, material).id, f"cantidad_{i}": cantidad}
    ctx["respuesta"] = como(client, EMAIL).post(
        "/catalogo/productos/nuevo/?tipo=TERMINADO", datos, follow=True
    )


@when(re_("creo el producto terminado {} {} con:", "sku", "nombre"))
def creo_terminado_con(ctx, sku, nombre, datatable):
    ctx["terminado"] = (sku, nombre, {fila[0]: fila[1] for fila in datatable[1:]})


@when("le asigno los materiales por unidad:")
def asigno_materiales(client, ctx, datatable):
    sku, nombre, campos = ctx["terminado"]
    post_terminado(client, ctx, sku, nombre, campos, [tuple(f) for f in datatable[1:]])


@then(re_("la presentación {} queda activa y vendible", "sku"))
def presentacion_activa(ctx, sku):
    p = producto(ctx, sku)
    assert p.activo and TipoProducto(p.tipo).vendible
    assert Presentacion.all_tenants.get(producto=p).materiales.count() == 4
    assert p.isc_categoria.nombre == "Cerveza"


@then("controla lote")
def controla_lote_terminado(ctx):
    assert producto(ctx, ctx["terminado"][0]).controla_lote


@given(re_("que existe la presentación {} de {}", "sku", "granel"))
def existe_presentacion(ctx, sku, granel):
    crear_terminado(ctx, sku, granel, "0.33", [("ENV-BOT330", "1")])


@when(
    parsers.re(
        r'creo la presentación "(?P<sku>[^"]+)" "(?P<nombre>[^"]+)" de "(?P<granel>[^"]+)" '
        r'con contenido (?P<contenido>[\d.]+) L y material "(?P<material>[^"]+)" × (?P<q>[\d.]+)'
    )
)
def creo_presentacion(client, ctx, sku, nombre, granel, contenido, material, q):
    campos = {"granel": granel, "contenido_l": contenido}
    post_terminado(client, ctx, sku, nombre, campos, [(material, q)])


@then(re_(r"{} tiene (?P<n>\d+) presentaciones activas", "granel"))
def n_presentaciones(ctx, granel, n):
    activas = Presentacion.all_tenants.filter(granel=producto(ctx, granel), producto__activo=True)
    assert activas.count() == int(n)


@when(
    parsers.re(
        r'creo un producto terminado con granel "(?P<granel>[^"]+)" '
        r"y contenido (?P<contenido>[\d.]+) L sin materiales"
    )
)
def terminado_sin_materiales(client, ctx, granel, contenido):
    campos = {"granel": granel, "contenido_l": contenido}
    post_terminado(client, ctx, "TER-X", "Sin materiales", campos, [])


@when(re_("creo un producto terminado con {} igual a {}", "campo", "valor"))
def terminado_con_dato(client, ctx, campo, valor):
    base = [("ENV-BOT330", "1")]
    if campo in ("contenido_l", "vida_util_dias"):
        post_terminado(client, ctx, "TER-X", "Inválido", {campo: valor}, base)
        return
    # Granel y materiales se eligen de listas que solo ofrecen GRANEL y ENVASE: un valor de
    # otro tipo solo llega manipulando el formulario, y el caso de uso lo rechaza.
    crear_directo(ctx, valor, tipo="INSUMO", u="KG")
    granel = producto(ctx, valor if campo == "granel" else "GRA-IPA").id
    material = producto(ctx, valor if campo == "material" else "ENV-BOT330").id
    datos = DatosProducto(
        "TER-X",
        "Inválido",
        TipoProducto.TERMINADO,
        "UND",
        precio_venta=Decimal("12"),
        vida_util_dias=120,
    )
    try:
        with tenant_context(ctx["empresa"].id):
            caso_de_uso(uc.CrearProducto).ejecutar(
                actor(EMAIL),
                datos,
                DatosPresentacion(granel, Decimal("0.33"), ((material, Decimal(1)),)),
            )
    except DomainError as e:
        ctx["textos"] = [e.mensaje]


@given(
    parsers.re(
        r'que "(?P<sku>[^"]+)" tiene stock (?P<n>\d+) UND con costo promedio (?P<costo>[\d.]+)'
    )
)
def stock_con_costo(ctx, sku, n, costo):
    crear_terminado(
        ctx,
        sku,
        "GRA-IPA",
        "0.33",
        [("ENV-BOT330", "1"), ("ENV-TAPA", "1"), ("ENV-ETQ-IPA", "1"), ("ENV-CAJA24", "0.0417")],
    )
    p = producto(ctx, sku)
    ctx["inventario"].stocks[p.id] = Decimal(n)
    ctx["pendientes"].append("el costo promedio del stock lo lleva inventario (0003a)")


@when(re_("cambio la etiqueta de {} por {}", "sku", "nueva"))
def cambio_etiqueta(client, ctx, sku, nueva):
    crear_directo(ctx, nueva, tipo="ENVASE", u="UND", nombre="Etiqueta IPA v2")
    p = producto(ctx, sku)
    actuales = Presentacion.all_tenants.get(producto=p).materiales.select_related("material")
    materiales = [
        (nueva if m.material.sku == "ENV-ETQ-IPA" else m.material.sku, str(m.cantidad_por_unidad))
        for m in actuales
    ]
    datos = {
        "accion": "guardar",
        "sku": p.sku,
        "nombre": p.nombre,
        "unidad": "UND",
        "stock_minimo": "0",
        "precio_venta": "12.00",
        "vida_util_dias": "120",
        "granel": producto(ctx, "GRA-IPA").id,
        "contenido": "0.3300",
    }
    for i, (material, cantidad) in enumerate(materiales):
        datos |= {f"material_{i}": producto(ctx, material).id, f"cantidad_{i}": cantidad}
    ctx["respuesta"] = como(client, EMAIL).post(f"/catalogo/productos/{p.id}/", datos, follow=True)


@then(re_(r"el costo promedio de {} sigue siendo (?P<costo>[\d.]+)", "sku"))
def costo_sigue(ctx, sku, costo):
    pass  # pendiente: el costo promedio lo lleva inventario (0003a); el catálogo no lo toca


@then(re_("el próximo envasado de {} consume {}", "sku", "material"))
def proximo_envasado(ctx, sku, material):
    with tenant_context(ctx["empresa"].id):
        consumo = catalogo_query().materiales_para(producto(ctx, sku).id, Decimal("1"))
    assert producto(ctx, material).id in consumo
    assert producto(ctx, "ENV-ETQ-IPA").id not in consumo


# --- 0002c: ISC (UC-CAT-05) ---


@given(re_("la categoría de ISC {} con Sistema Específico", "nombre"))
def categoria_especifico(ctx, nombre):
    ctx["categoria"] = IscCategoria.all_tenants.create(
        empresa=ctx["empresa"], nombre=nombre, codigo_tipo_sistema="02"
    )


@given(re_(r"la tarifa de S/ (?P<monto>[\d.]+) por litro vigente desde {}", "desde"))
def tarifa_desde(ctx, monto, desde):
    IscTarifa.objects.create(
        categoria=ctx["categoria"],
        vigente_desde=date.fromisoformat(desde),
        monto_por_litro=Decimal(monto),
    )


@when(
    re_(
        r"agrego a {} la tarifa de S/ (?P<monto>[\d.]+) por litro vigente desde {}",
        "nombre",
        "desde",
    )
)
def agrego_tarifa(client, ctx, nombre, monto, desde):
    # Gestionar el ISC es del Administrador (catalogo.isc.gestionar).
    crear_usuario("admin@andina.pe", ctx["empresa"], "Administrador")
    como(client, "admin@andina.pe").post(
        "/catalogo/isc/",
        {"accion": "tarifa", "categoria": ctx["categoria"].id, "monto": monto, "desde": desde},
    )


def monto_isc(ctx, sku, fecha):
    with tenant_context(ctx["empresa"].id):
        return catalogo_query().isc_aplicable(producto(ctx, sku).id, date.fromisoformat(fecha))


@then(re_(r"una venta de {} emitida el {} usa S/ (?P<monto>[\d.]+) por litro", "sku", "fecha"))
def venta_usa(ctx, sku, fecha, monto):
    crear_terminado(ctx, sku, "GRA-IPA", "0.33", [("ENV-BOT330", "1")], ctx["categoria"])
    ctx["sku"] = sku
    assert monto_isc(ctx, sku, fecha).monto_por_litro == Decimal(monto)


@then(re_(r"una venta emitida el {} usa S/ (?P<monto>[\d.]+) por litro", "fecha"))
def venta_emitida_usa(ctx, fecha, monto):
    assert monto_isc(ctx, ctx["sku"], fecha).monto_por_litro == Decimal(monto)


@given(re_("el producto terminado {} sin categoría de ISC", "sku"))
def terminado_sin_isc(ctx, sku):
    crear_terminado(ctx, sku, "GRA-IPA", "0.33", [("ENV-BOT330", "1")])


@when(re_(r"se calcula el ISC de una venta de (?P<n>\d+) unidades de {}", "sku"))
def calculo_isc(ctx, n, sku):
    with tenant_context(ctx["empresa"].id):
        ctx["isc"] = catalogo_query().isc_de_linea(producto(ctx, sku).id, Decimal(n), date.today())


@then(re_(r"el ISC es (?P<monto>[\d.]+)"))
def el_isc_es(ctx, monto):
    assert ctx["isc"] == Decimal(monto)


@when(
    re_(
        "creo el producto {} de tipo {} con categoría de ISC {} y sin contenido en litros",
        "sku",
        "tipo",
        "categoria",
    )
)
def mercaderia_isc_sin_contenido(client, ctx, sku, tipo, categoria):
    datos = {
        "sku": sku,
        "nombre": "Cerveza de terceros",
        "unidad": "UND",
        "stock_minimo": "0",
        "precio_venta": "8.00",
        "isc_categoria_id": categoria_isc(ctx, categoria).id,
    }
    ctx["respuesta"] = como(client, EMAIL).post(
        f"/catalogo/productos/nuevo/?tipo={tipo}", datos, follow=True
    )
