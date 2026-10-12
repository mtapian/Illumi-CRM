"""Pasos de los escenarios del catálogo (épica 0002): bienes y servicios, receta, ISC."""

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from pytest_bdd import given, parsers, then, when

from catalog.application import productos as uc
from catalog.domain.producto import DatosProducto
from catalog.domain.tipos import TipoProducto
from catalog.infrastructure.contenedor import (
    caso_de_uso,
    catalogo_query,
    sembrar_impuestos,
    sembrar_unidades,
)
from catalog.infrastructure.models import (
    Categoria,
    Marca,
    Producto,
    ProductoIscTasa,
    RecetaComponente,
    Unidad,
)
from catalog.infrastructure.repositorios import CatalogoOrm
from shared.domain.accesos import CATALOGO
from shared.domain.errores import DomainError
from shared.domain.tenant import tenant_context
from tenancy.infrastructure.contenedor import tenancy_service
from tenancy.infrastructure.models import ParametroVigencia, PlanFuncionalidad
from tests.acceptance.conftest import contenido
from tests.acceptance.pasos_accesos import actor, como, re_
from tests.acceptance.pasos_sesion import crear_empresa, crear_usuario

ROLES = {"gerente": "Gerente", "produccion": "Producción", "almacen": "Almacén"}
ROLES["administrador"] = "Administrador"  # gestiona el ISC (0001c)
EMAIL = "yo@andina.pe"


def producto(ctx, sku: str) -> Producto:
    return Producto.all_tenants.get(empresa=ctx["empresa"], sku=sku)


def unidad(ctx, abreviatura: str) -> Unidad:
    return Unidad.all_tenants.get(empresa=ctx["empresa"], abreviatura=abreviatura)


def crear_directo(ctx, sku, u="KG", nombre=None, **kw) -> Producto:
    """Por defecto, un bien que se compra (RF-CAT-38)."""
    existente = Producto.all_tenants.filter(empresa=ctx["empresa"], sku=sku).first()
    if existente:
        return existente
    return Producto.all_tenants.create(
        empresa=ctx["empresa"], sku=sku, nombre=nombre or sku, unidad=unidad(ctx, u), **kw
    )


def crear_fabricado(ctx, sku, receta, tasa=None, nombre=None, contenido="0.33"):
    """Bien que se fabrica y se vende, con su receta [(sku, cantidad)] (RF-CAT-41) y, si se
    indica `tasa` (monto por litro), afecto a ISC desde el 2024-07-01 (RF-CAT-45)."""
    existente = Producto.all_tenants.filter(empresa=ctx["empresa"], sku=sku).first()
    if existente:
        return existente
    isc = {}
    if tasa:
        isc = {"isc_sistema": "ESPECIFICO", "isc_codigo_tipo_sistema": "02"}
        isc["contenido_litros"] = Decimal(contenido)
    p = crear_directo(
        ctx,
        sku,
        u="UND",
        nombre=nombre,
        se_vende=True,
        se_compra=False,
        se_fabrica=True,
        precio_venta=Decimal("12"),
        vida_util_dias=120,
        **isc,
    )
    for componente, cantidad in receta:
        RecetaComponente.objects.create(
            producto=p, componente=producto(ctx, componente), cantidad_por_unidad=Decimal(cantidad)
        )
    if tasa:
        agregar_tasa(ctx, p, tasa, "2024-07-01")
    return p


def agregar_tasa(ctx, p, monto, desde):
    ProductoIscTasa.all_tenants.create(
        empresa=ctx["empresa"],
        producto_id=p.id,
        monto_por_litro=Decimal(monto),
        vigente_desde=date.fromisoformat(desde),
    )


def casillas(texto: str) -> dict:
    """ "se compra, se vende" → {"se_compra": "on", "se_vende": "on"}."""
    return {c.strip().replace(" ", "_"): "on" for c in texto.split(",") if c.strip()}


def post_producto(client, ctx, **campos):
    """Alta por la pantalla; por defecto un bien que se compra."""
    datos = {"tipo": "BIEN", "se_compra": "on", "nombre": campos.get("sku", "x")} | campos
    datos = {k: v for k, v in datos.items() if v is not None}
    ctx["respuesta"] = como(client, EMAIL).post("/catalogo/productos/nuevo/", datos, follow=True)


def post_ficha(client, ctx, codigo, email=EMAIL, **campos):
    """Guarda la ficha con sus valores actuales y los `campos` cambiados (None = vaciar)."""
    p = producto(ctx, codigo)
    datos = {
        "accion": "guardar",
        "tipo": p.tipo,
        "sku": p.sku,
        "nombre": p.nombre,
        "unidad": p.unidad.abreviatura,
        "stock_minimo": str(p.stock_minimo),
        "precio_venta": p.precio_venta,
        "vida_util_dias": p.vida_util_dias,
        "contenido_litros": p.contenido_litros,
        "afecto_isc": "on" if p.isc_sistema else None,
        "isc_codigo_tipo_sistema": p.isc_codigo_tipo_sistema,
        "categoria": p.categoria_id,
        "marca": p.marca_id,
        "codigo_barras": p.codigo_barras,
        "referencia": p.referencia,
    }
    datos |= {c: "on" for c in ("se_vende", "se_compra", "se_fabrica") if getattr(p, c)}
    for i, r in enumerate(RecetaComponente.objects.filter(producto=p).order_by("id")):
        datos |= {f"componente_{i}": r.componente_id, f"cantidad_{i}": r.cantidad_por_unidad}
    datos = {k: v for k, v in (datos | campos).items() if v is not None}
    return como(client, email).post(f"/catalogo/productos/{p.id}/", datos, follow=True)


# --- Antecedentes ---


@given(re_("que soy usuario {} de {}", "rol", "nombre"))
def soy_usuario(client, ctx, inventario, rol, nombre):
    ctx["empresa"] = crear_empresa(nombre)
    for f in CATALOGO:
        PlanFuncionalidad.objects.create(plan=ctx["empresa"].plan, funcionalidad_id=f)
    usuario = crear_usuario(EMAIL, ctx["empresa"], ROLES[rol])
    sembrar_unidades(ctx["empresa"].id, usuario.id, date.today())
    # Un test transaccional vacía la tabla: se repone el IGV de la plataforma (migración 0004).
    ParametroVigencia.objects.get_or_create(
        empresa=None, clave="igv_pct", vigente_desde=date(2011, 3, 1), defaults={"valor": 18}
    )
    sembrar_impuestos(ctx["empresa"].id, usuario.id, date.today())  # RF-CAT-52
    ctx["inventario"] = inventario


@given(re_("existen las unidades {}", "lista"))
def existen_unidades(ctx, lista):
    existentes = set(
        Unidad.all_tenants.filter(empresa=ctx["empresa"]).values_list("abreviatura", flat=True)
    )
    assert {u.strip() for u in lista.split(",")} <= existentes


# --- Crear bienes y servicios (UC-CAT-02, 08) ---


@when(
    parsers.re(
        r'creo el (?P<tipo>bien|servicio) "(?P<sku>[^"]+)" "(?P<nombre>[^"]+)" en "(?P<u>[^"]+)" '
        r'que "(?P<gestion>[^"]+)" con precio "(?P<precio>[^"]*)"'
    )
)
def creo_bien_o_servicio(client, ctx, tipo, sku, nombre, u, gestion, precio):
    datos = {"tipo": tipo.upper(), "sku": sku, "nombre": nombre, "unidad": u}
    datos |= {"se_compra": None} | casillas(gestion) | {"precio_venta": precio or None}
    post_producto(client, ctx, **datos)


@then(re_("el producto {} queda activo con stock 0", "sku"))
def queda_activo(ctx, sku):
    p = producto(ctx, sku)
    assert p.activo and ctx["inventario"].stock(p.id) == 0
    ctx["sku"] = sku


@then(re_("su gestión es {}", "gestion"))
def su_gestion(ctx, gestion):
    p = producto(ctx, ctx["sku"])
    marcadas = {c for c in ("se_vende", "se_compra", "se_fabrica") if getattr(p, c)}
    assert marcadas == set(casillas(gestion))


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
    post_producto(client, ctx, sku=sku, nombre="Otra malta", unidad="KG")


@given(re_("que {} tiene el producto con SKU {}", "nombre", "sku"))
def otra_empresa_tiene(nombre, sku):
    otra = crear_empresa(nombre)
    und = Unidad.all_tenants.create(
        empresa=otra, nombre="Kilogramo", abreviatura="KG", codigo_sunat="KGM"
    )
    Producto.all_tenants.create(empresa=otra, sku=sku, nombre=sku, unidad=und)


@when(re_("creo un producto con SKU {} en {}", "sku", "nombre"))
def creo_en(client, ctx, sku, nombre):
    post_producto(client, ctx, sku=sku, nombre="Malta", unidad="KG")


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
        servicio = {"tipo": TipoProducto.SERVICIO, "se_vende": True, "precio_venta": Decimal(1)}
        for cambio in ({"sku": "INS-OTRO"}, servicio, {"unidad": "G"}):
            try:
                caso_de_uso(uc.EditarProducto).ejecutar(
                    actor(EMAIL), p.id, replace(datos, **cambio)
                )
            except DomainError as e:
                ctx["textos"].append(e.mensaje)
    assert len(ctx["textos"]) == 3


@then("puedo cambiar su nombre, categoría y stock mínimo")
def puedo_cambiar(client, ctx):
    categoria = Categoria.all_tenants.create(empresa=ctx["empresa"], nombre="Maltas")
    post_ficha(
        client,
        ctx,
        "INS-MALTA",
        nombre="Malta Pilsen",
        categoria=categoria.id,
        stock_minimo="25",
    )
    p = producto(ctx, "INS-MALTA")
    assert (p.nombre, p.categoria_id, p.stock_minimo) == (
        "Malta Pilsen",
        categoria.id,
        Decimal("25"),
    )


@given(re_(r"que el plan de la empresa permite (?P<n>\d+) productos activos"))
def plan_permite(ctx, n):
    ctx["empresa"].plan.limite_productos = int(n)
    ctx["empresa"].plan.save()


@given(re_(r"la empresa tiene (?P<n>\d+) productos activos"))
def tiene_n_activos(ctx, n):
    und = unidad(ctx, "UND")
    Producto.all_tenants.bulk_create(
        Producto(empresa=ctx["empresa"], sku=f"ENV-{i}", nombre=f"Envase {i}", unidad=und)
        for i in range(int(n))
    )


@when("creo un producto nuevo")
def creo_nuevo(client, ctx):
    post_producto(client, ctx, sku="ENV-NUEVO", nombre="Nuevo", unidad="UND")


@given(re_("que la unidad {} está asignada a {}", "u", "sku"))
def unidad_asignada(ctx, u, sku):
    crear_directo(ctx, sku, u=u)


@when(re_("intento eliminar la unidad {}", "u"))
def elimino_unidad(client, ctx, u):
    ctx["respuesta"] = como(client, EMAIL).post(
        "/catalogo/unidades/", {"accion": "eliminar", "id": unidad(ctx, u).id}, follow=True
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
def no_aparece(client, ctx):
    with tenant_context(ctx["empresa"].id):
        ofrecidos = {p.sku for p in catalogo_query().activos(se_compra=True)}
    assert ctx["sku"] not in ofrecidos
    assert ctx["sku"] not in contenido(como(client, EMAIL).get("/compras/nueva/"))
    ctx["pendientes"].append("la pantalla de recetas (0005a) usa CatalogoQuery.activos")


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
    crear_directo(ctx, sku, u="UND")
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


# --- Bien de reventa (RF-CAT-39, 40) ---


@when(re_("creo el bien {} {} que se compra y se vende con:", "sku", "nombre"))
def creo_bien_con_tabla(client, ctx, sku, nombre, datatable):
    campos = {fila[0]: fila[1] for fila in datatable[1:]}
    post_producto(client, ctx, sku=sku, nombre=nombre, se_vende="on", **campos)


@then(re_("{} queda activo, se compra y se vende", "sku"))
def activo_compra_vende(ctx, sku):
    p = producto(ctx, sku)
    assert p.activo and p.se_compra and p.se_vende and not p.se_fabrica
    ctx["sku"] = sku


@then("no tiene receta")
def no_tiene_receta(ctx):
    assert not RecetaComponente.objects.filter(producto=producto(ctx, ctx["sku"])).exists()


@then("no paga ISC porque no está afecto a ISC")
def sin_isc(ctx):
    assert producto(ctx, ctx["sku"]).isc_sistema is None


# --- Receta (0002b reformulada; RF-CAT-41) ---


@given(re_(r"existe el bien que se fabrica {} \((?P<nombre>[^)]+)\)", "sku"))
def existe_fabricado(ctx, sku, nombre):
    crear_directo(ctx, sku, u="L", nombre=nombre, se_compra=False, se_fabrica=True)


@given("existen los bienes que se compran:")
def existen_comprables(ctx, datatable):
    for sku, nombre in datatable[1:]:
        crear_directo(ctx, sku, u="UND", nombre=nombre)


def post_fabricado(client, ctx, sku, nombre, campos, receta, vende=True):
    datos = {
        "sku": sku,
        "nombre": nombre,
        "unidad": "UND",
        "se_compra": None,
        "se_fabrica": "on",
        "se_vende": "on" if vende else None,
        "precio_venta": campos.get("precio_venta", "12.00") if vende else None,
        "vida_util_dias": campos.get("vida_util_dias"),
        "contenido_litros": campos.get("contenido_l"),
    }
    if campos.get("tasa_isc"):
        datos |= {"afecto_isc": "on", "isc_codigo_tipo_sistema": "02"}
        datos |= {"tasa_monto": campos["tasa_isc"], "tasa_desde": "2024-07-01"}
    for i, (componente, cantidad) in enumerate(receta):
        datos |= {f"componente_{i}": producto(ctx, componente).id, f"cantidad_{i}": cantidad}
    post_producto(client, ctx, **datos)


@when(re_("creo el bien {} {} que se fabrica y se vende con:", "sku", "nombre"))
def creo_fabricado_con(ctx, sku, nombre, datatable):
    ctx["fabricado"] = (sku, nombre, {fila[0]: fila[1] for fila in datatable[1:]})


@when("le asigno la receta por unidad:")
def asigno_receta(client, ctx, datatable):
    sku, nombre, campos = ctx["fabricado"]
    post_fabricado(client, ctx, sku, nombre, campos, [tuple(f) for f in datatable[1:]])


@then(re_(r"{} queda activo y vendible con (?P<n>\d+) componentes en su receta", "sku"))
def fabricado_activo(ctx, sku, n):
    p = producto(ctx, sku)
    assert p.activo and p.se_vende and p.se_fabrica
    assert RecetaComponente.objects.filter(producto=p).count() == int(n)


@given(re_("que existe el bien {} con {} en su receta", "sku", "granel"))
def existe_con_receta(ctx, sku, granel):
    crear_fabricado(ctx, sku, [(granel, "0.33"), ("ENV-BOT330", "1")])


@when(
    parsers.re(
        r'creo el bien "(?P<sku>[^"]+)" "(?P<nombre>[^"]+)" que se fabrica con receta '
        r'"(?P<a>[^"]+)" × (?P<qa>[\d.]+) y "(?P<b>[^"]+)" × (?P<qb>[\d.]+)'
    )
)
def creo_con_receta_de_dos(client, ctx, sku, nombre, a, qa, b, qb):
    post_fabricado(client, ctx, sku, nombre, {}, [(a, qa), (b, qb)], vende=False)


@then(re_(r"{} está en la receta de (?P<n>\d+) productos activos", "sku"))
def en_receta_de(ctx, sku, n):
    usos = RecetaComponente.objects.filter(componente=producto(ctx, sku), producto__activo=True)
    assert usos.count() == int(n)


@when(re_("creo el bien {} {} que se fabrica y se vende sin receta", "sku", "nombre"))
def creo_sin_receta(client, ctx, sku, nombre):
    post_fabricado(client, ctx, sku, nombre, {}, [])


@then(re_("{} se crea sin receta", "sku"))
def se_crea_sin_receta(ctx, sku):
    assert not RecetaComponente.objects.filter(producto=producto(ctx, sku)).exists()


@when(re_("creo un bien que se fabrica con {} igual a {}", "campo", "valor"))
def fabricado_con_dato(client, ctx, campo, valor):
    receta = [("GRA-IPA", "0.33"), ("ENV-BOT330", "1")]
    if campo == "cantidad":
        post_fabricado(client, ctx, "TER-X", "Inválido", {}, [("GRA-IPA", valor)])
        return
    if campo == "repetido":
        post_fabricado(client, ctx, "TER-X", "Inválido", {}, [*receta, (valor, "1")])
        return
    # La pantalla no ofrece vida útil 0 ni componentes inactivos: el caso de uso los rechaza.
    if campo == "inactivo":
        Producto.all_tenants.filter(empresa=ctx["empresa"], sku=valor).update(activo=False)
        receta = [(valor, "1")]
    datos = DatosProducto(
        "TER-X",
        "Inválido",
        TipoProducto.BIEN,
        "UND",
        se_compra=False,
        se_fabrica=True,
        vida_util_dias=int(valor) if campo == "vida_util_dias" else None,
    )
    try:
        with tenant_context(ctx["empresa"].id):
            ids = tuple((producto(ctx, c).id, Decimal(q)) for c, q in receta)
            caso_de_uso(uc.CrearProducto).ejecutar(actor(EMAIL), datos, ids)
    except DomainError as e:
        ctx["textos"] = [e.mensaje]


@given(
    parsers.re(
        r'que "(?P<sku>[^"]+)" tiene stock (?P<n>\d+) UND con costo promedio (?P<costo>[\d.]+)'
    )
)
def stock_con_costo(ctx, sku, n, costo):
    receta = [("GRA-IPA", "0.33"), ("ENV-BOT330", "1"), ("ENV-TAPA", "1"), ("ENV-ETQ-IPA", "1")]
    crear_fabricado(ctx, sku, [*receta, ("ENV-CAJA24", "0.0417")])
    p = producto(ctx, sku)
    ctx["inventario"].stocks[p.id] = Decimal(n)  # lo que ve el catálogo por su puerto
    from inventory.application.servicio import Linea
    from inventory.infrastructure.contenedor import inventario
    from inventory.infrastructure.models import Almacen

    with tenant_context(ctx["empresa"].id), transaction.atomic():
        principal = Almacen.objects.get_or_create(nombre="Principal")[0].id
        linea = Linea(p.id, principal, Decimal(n), Decimal(costo))
        inventario().registrar_entrada("SALDO_INICIAL", "AJUSTE", 1, [linea], None, date.today())


@when(re_("cambio la etiqueta en la receta de {} por {}", "sku", "nueva"))
def cambio_etiqueta(client, ctx, sku, nueva):
    crear_directo(ctx, nueva, u="UND", nombre="Etiqueta IPA v2")
    p = producto(ctx, sku)
    etiqueta = RecetaComponente.objects.get(producto=p, componente=producto(ctx, "ENV-ETQ-IPA"))
    i = list(RecetaComponente.objects.filter(producto=p).order_by("id")).index(etiqueta)
    ctx["respuesta"] = post_ficha(client, ctx, sku, **{f"componente_{i}": producto(ctx, nueva).id})


@then(re_(r"el costo promedio de {} sigue siendo (?P<costo>[\d.]+)", "sku"))
def costo_sigue(ctx, sku, costo):
    from inventory.infrastructure.models import CostoProducto

    c = CostoProducto.all_tenants.get(producto=producto(ctx, sku))
    assert c.costo_promedio == Decimal(costo)  # cambiar la receta no toca el costo (RF-CAT-18)


@then(re_("la próxima producción de {} consume {}", "sku", "componente"))
def proxima_produccion(ctx, sku, componente):
    with tenant_context(ctx["empresa"].id):
        consumo = catalogo_query().componentes_para(producto(ctx, sku).id, Decimal("1"))
    assert producto(ctx, componente).id in consumo
    assert producto(ctx, "ENV-ETQ-IPA").id not in consumo


# --- 0002c: ISC (UC-CAT-05) ---


@given(
    re_(
        r"el bien {} afecto a ISC con tasa de S/ (?P<monto>[\d.]+) por litro vigente desde {}",
        "sku",
        "desde",
    )
)
def bien_afecto(ctx, sku, monto, desde):
    crear_directo(ctx, "GRA-IPA", u="L", se_compra=False, se_fabrica=True)
    crear_directo(ctx, "ENV-BOT330", u="UND")
    p = crear_fabricado(ctx, sku, [("GRA-IPA", "0.33"), ("ENV-BOT330", "1")])
    Producto.all_tenants.filter(pk=p.pk).update(
        isc_sistema="ESPECIFICO", isc_codigo_tipo_sistema="02", contenido_litros=Decimal("0.33")
    )
    agregar_tasa(ctx, p, monto, desde)
    ctx["sku"] = sku


@when(
    re_(
        r"agrego a {} la tasa de S/ (?P<monto>[\d.]+) por litro vigente desde {}",
        "sku",
        "desde",
    )
)
def agrego_tasa(client, ctx, sku, monto, desde):
    # Gestionar el ISC es del Administrador (catalogo.isc.gestionar).
    crear_usuario("admin@andina.pe", ctx["empresa"], "Administrador")
    post_ficha(client, ctx, sku, tasa_monto=monto, tasa_desde=desde, email="admin@andina.pe")


def monto_isc(ctx, sku, fecha):
    with tenant_context(ctx["empresa"].id):
        return catalogo_query().isc_aplicable(producto(ctx, sku).id, date.fromisoformat(fecha))


@then(re_(r"una venta de {} emitida el {} usa S/ (?P<monto>[\d.]+) por litro", "sku", "fecha"))
def venta_usa(ctx, sku, fecha, monto):
    assert monto_isc(ctx, sku, fecha).monto_por_litro == Decimal(monto)


@then(re_(r"una venta emitida el {} usa S/ (?P<monto>[\d.]+) por litro", "fecha"))
def venta_emitida_usa(ctx, fecha, monto):
    assert monto_isc(ctx, ctx["sku"], fecha).monto_por_litro == Decimal(monto)


@given(re_("el bien {} que se vende sin ISC", "sku"))
def vendible_sin_isc(ctx, sku):
    crear_fabricado(ctx, sku, [("GRA-IPA", "0.33"), ("ENV-BOT330", "1")])


@when(re_(r"se calcula el ISC de una venta de (?P<n>\d+) unidades de {}", "sku"))
def calculo_isc(ctx, n, sku):
    with tenant_context(ctx["empresa"].id):
        ctx["isc"] = catalogo_query().isc_de_linea(producto(ctx, sku).id, Decimal(n), date.today())


@then(re_(r"el ISC es (?P<monto>[\d.]+)"))
def el_isc_es(ctx, monto):
    assert ctx["isc"] == Decimal(monto)


@when(
    re_(
        "creo el bien {} que se vende afecto a ISC y sin contenido en litros",
        "sku",
    )
)
def vendible_isc_sin_contenido(client, ctx, sku):
    post_producto(
        client,
        ctx,
        sku=sku,
        nombre="Cerveza de terceros",
        unidad="UND",
        se_vende="on",
        precio_venta="8.00",
        afecto_isc="on",
        isc_codigo_tipo_sistema="02",
        tasa_monto="2.51",
        tasa_desde="2024-07-01",
    )


# --- Enmienda 1: ficha estilo Odoo (UC-CAT-06; RF-CAT-04, 29 a 32) ---

CLAVE_PESTANA = {"General": "general", "Ventas": "ventas", "Compras": "compras"}
CLAVE_PESTANA |= {"Inventario": "inventario", "Producción": "produccion"}


def abrir_ficha(client, ctx, sku):
    respuesta = como(client, EMAIL).get(f"/catalogo/productos/{producto(ctx, sku).id}/")
    ctx["ficha"] = respuesta.content.decode()
    return ctx["ficha"]


def tiene_pestana(html, etiqueta):
    """Visible al cargar la ficha; las casillas la ocultan o muestran en vivo (CSS)."""
    return f'for="pes-{CLAVE_PESTANA[etiqueta]}" data-activa="si"' in html


@when(re_("abro la ficha de {}", "sku"))
def abro_ficha(client, ctx, sku):
    abrir_ficha(client, ctx, sku)


@then(re_("veo las pestañas {}, {} e {} y no veo {} ni {}", "a", "b", "c", "d", "e"))
def veo_pestanas(ctx, a, b, c, d, e):
    for etiqueta in (a, b, c):
        assert tiene_pestana(ctx["ficha"], etiqueta), etiqueta
    for etiqueta in (d, e):
        assert not tiene_pestana(ctx["ficha"], etiqueta), etiqueta


@when(re_(r"marco que {} se vende con precio (?P<precio>[\d.]+)", "sku"))
def marco_se_vende(client, ctx, sku, precio):
    post_ficha(client, ctx, sku, se_vende="on", precio_venta=precio)


@then(re_("{} se vende y veo la pestaña {}", "sku", "pestana"))
def se_vende_y_pestana(client, ctx, sku, pestana):
    assert producto(ctx, sku).se_vende
    assert tiene_pestana(abrir_ficha(client, ctx, sku), pestana)


@when(re_("intento cambiar su tipo a {}", "tipo"))
def intento_cambiar_tipo(client, ctx, tipo):
    p = producto(ctx, "INS-MALTA")
    # En pantalla el tipo queda bloqueado (disabled): lo enviado se ignora.
    post_ficha(client, ctx, "INS-MALTA", tipo=tipo, se_vende="on", precio_venta="1")
    assert producto(ctx, "INS-MALTA").tipo == p.tipo
    ctx["textos"] = []
    with tenant_context(ctx["empresa"].id):
        datos = replace(
            CatalogoOrm().producto(p.id),
            tipo=TipoProducto(tipo),
            se_vende=True,
            precio_venta=Decimal("1"),
        )
        try:
            caso_de_uso(uc.EditarProducto).ejecutar(actor(EMAIL), p.id, datos)
        except DomainError as e:
            ctx["textos"].append(e.mensaje)
    assert ctx["textos"]


@given(re_(r"que el IGV vigente es (?P<pct>\d+) %"))
def igv_vigente(ctx, pct):
    with tenant_context(ctx["empresa"].id):
        assert tenancy_service().igv_vigente(date.today()) == Decimal(pct)


@given(
    re_(
        r"el bien {} de (?P<litros>[\d.]+) L que se vende a (?P<precio>[\d.]+)"
        r" afecto a ISC con tasa de S/ (?P<monto>[\d.]+) por litro",
        "sku",
    )
)
def vendible_con_isc(ctx, sku, litros, precio, monto):
    crear_directo(ctx, "GRA-IPA", u="L", se_compra=False, se_fabrica=True)
    crear_directo(ctx, "ENV-BOT330", u="UND")
    receta = [("GRA-IPA", litros), ("ENV-BOT330", "1")]
    p = crear_fabricado(ctx, sku, receta, monto, contenido=litros)
    Producto.all_tenants.filter(pk=p.pk).update(precio_venta=Decimal(precio))


@then(re_("veo el desglose {}", "texto"))
def veo_desglose(ctx, texto):
    assert texto in ctx["ficha"]


@given(re_("que el producto {} tiene el código de barras {}", "sku", "codigo"))
def tiene_codigo_barras(ctx, sku, codigo):
    crear_directo(ctx, sku, u="UND", codigo_barras=codigo)


@when(re_("asigno el código de barras {} a {}", "codigo", "sku"))
def asigno_codigo(client, ctx, codigo, sku):
    crear_directo(ctx, sku)
    ctx["respuesta"] = post_ficha(client, ctx, sku, codigo_barras=codigo)
    assert producto(ctx, sku).codigo_barras == ""


@when(re_(r"cambio su nombre a {} y su stock mínimo a (?P<n>\d+)", "nombre"))
def cambio_nombre_y_minimo(client, ctx, nombre, n):
    post_ficha(client, ctx, "INS-MALTA", nombre=nombre, stock_minimo=n)


@then(re_("el historial de {} muestra mi usuario, la fecha y {}", "sku", "texto"))
def historial_muestra(client, ctx, sku, texto):
    html = abrir_ficha(client, ctx, sku)
    assert EMAIL in html and f"{date.today():%d/%m/%Y}" in html
    assert texto in html


@then(re_("muestra {}", "texto"))
def muestra(ctx, texto):
    assert texto in ctx["ficha"]


# --- Enmienda 2: maestros del catálogo (UC-CAT-07; RF-CAT-33 a 36) ---


def marca(ctx, nombre) -> Marca:
    return Marca.all_tenants.get(empresa=ctx["empresa"], nombre=nombre)


def post_marca(client, ctx, **datos):
    ctx["respuesta"] = como(client, EMAIL).post("/catalogo/marcas/", datos, follow=True)


@when(re_("creo la marca {}", "nombre"))
def creo_marca(client, ctx, nombre):
    post_marca(client, ctx, accion="guardar", nombre=nombre)


@when(re_("asigno la marca {} a {}", "nombre", "sku"))
def asigno_marca(client, ctx, nombre, sku):
    crear_directo(ctx, sku)
    post_ficha(client, ctx, sku, marca=marca(ctx, nombre).id)
    assert producto(ctx, sku).marca.nombre == nombre


def fila_marca(html, nombre, n):
    return f"<strong>{nombre}</strong>" in html and f'<span class="chip neutro">{n}</span>' in html


@then(re_(r"el listado de marcas muestra {} con (?P<n>\d+) producto", "nombre"))
def listado_marcas(client, ctx, nombre, n):
    assert fila_marca(contenido(como(client, EMAIL).get("/catalogo/marcas/")), nombre, n)


@then(re_("buscar {} en marcas muestra {}", "q", "nombre"))
def buscar_marcas(client, ctx, q, nombre):
    html = contenido(como(client, EMAIL).get("/catalogo/marcas/", {"q": q}))
    assert f"<strong>{nombre}</strong>" in html


@given(re_("que la marca {} la usa el producto {}", "nombre", "sku"))
def marca_en_uso(ctx, nombre, sku):
    m = Marca.all_tenants.create(empresa=ctx["empresa"], nombre=nombre)
    crear_directo(ctx, sku, marca=m)


@when(re_("intento eliminar la marca {}", "nombre"))
def elimino_marca(client, ctx, nombre):
    post_marca(client, ctx, accion="eliminar", id=marca(ctx, nombre).id)
    assert Marca.all_tenants.filter(empresa=ctx["empresa"], nombre=nombre).exists()


@when(re_("desactivo la marca {}", "nombre"))
def desactivo_marca(client, ctx, nombre):
    post_marca(client, ctx, accion="desactivar", id=marca(ctx, nombre).id)
    assert not marca(ctx, nombre).activo


@then(
    re_("{} conserva la marca {} y la marca ya no se ofrece en productos nuevos", "sku", "nombre")
)
def conserva_marca(client, ctx, sku, nombre):
    assert producto(ctx, sku).marca.nombre == nombre
    html = contenido(como(client, EMAIL).get("/catalogo/productos/nuevo/"))
    assert f">{nombre}</option>" not in html


@when(re_("edito la unidad {} con nombre {} y abreviatura {}", "u", "nombre", "abrev"))
def edito_unidad(client, ctx, u, nombre, abrev):
    datos = {"accion": "guardar", "id": unidad(ctx, u).id, "nombre": nombre}
    datos |= {"abreviatura": abrev, "codigo_sunat": unidad(ctx, u).codigo_sunat}
    ctx["respuesta"] = como(client, EMAIL).post("/catalogo/unidades/", datos, follow=True)


@then(re_("la unidad {} se llama {}", "u", "nombre"))
def unidad_se_llama(ctx, u, nombre):
    assert unidad(ctx, u).nombre == nombre


# --- Enmienda 4: bien o servicio, casillas y receta (UC-CAT-08; RF-CAT-37 a 43) ---


@when(re_(r"creo el servicio {} {} que se vende a (?P<precio>[\d.]+)", "sku", "nombre"))
def creo_servicio(client, ctx, sku, nombre, precio):
    datos = {"tipo": "SERVICIO", "se_compra": None, "se_vende": "on", "unidad": "SERV"}
    post_producto(client, ctx, sku=sku, nombre=nombre, precio_venta=precio, **datos)


@then(re_("{} no tiene stock, lote ni pestaña Inventario", "sku"))
def servicio_sin_inventario(client, ctx, sku):
    p = producto(ctx, sku)
    assert p.tipo == "SERVICIO" and ctx["inventario"].stock(p.id) == 0
    assert not tiene_pestana(abrir_ficha(client, ctx, sku), "Inventario")


@then(re_("veo la pestaña {}", "pestana"))
def veo_pestana(ctx, pestana):
    assert tiene_pestana(ctx["ficha"], pestana)


@when(re_("creo un bien {} sin marcar se vende, se compra ni se fabrica", "sku"))
def creo_sin_casillas(client, ctx, sku):
    post_producto(client, ctx, sku=sku, nombre="Sin casillas", unidad="KG", se_compra=None)


@given(re_("que existen los bienes {} que se fabrica, {} e {} que se compran", "a", "b", "c"))
def existen_bienes(ctx, a, b, c):
    crear_directo(ctx, a, u="L", se_compra=False, se_fabrica=True)
    crear_directo(ctx, b, u="UND")
    crear_directo(ctx, c)


@when(
    re_(
        r"creo el bien {} que se fabrica y se vende a (?P<precio>[\d.]+) con vida útil "
        r"(?P<dias>\d+) días y receta:",
        "sku",
    )
)
def creo_fabricado_con_receta(client, ctx, sku, precio, dias, datatable):
    campos = {"precio_venta": precio, "vida_util_dias": dias}
    post_fabricado(client, ctx, sku, sku, campos, [tuple(f) for f in datatable[1:]])


@then(re_(r"la receta de {} tiene (?P<n>\d+) componentes?", "sku"))
def receta_tiene(ctx, sku, n):
    assert RecetaComponente.objects.filter(producto=producto(ctx, sku)).count() == int(n)


@then(re_("{} no puede ser componente de sí mismo", "sku"))
def no_es_su_componente(client, ctx, sku):
    p = producto(ctx, sku)
    html = abrir_ficha(client, ctx, sku)
    assert f'<option value="{p.id}"' not in html  # la pantalla no lo ofrece
    with tenant_context(ctx["empresa"].id):
        datos = CatalogoOrm().producto(p.id)
        try:
            caso_de_uso(uc.EditarProducto).ejecutar(actor(EMAIL), p.id, datos, ((p.id, 1),))
            raise AssertionError("debió rechazarse")
        except DomainError as e:
            assert "componente de sí mismo" in e.mensaje


@when(re_(r"registro en {} peso (?P<peso>[\d.]+) kg y volumen (?P<volumen>[\d.]+) m³", "sku"))
def registro_peso_volumen(client, ctx, sku, peso, volumen):
    crear_directo(ctx, sku)
    post_ficha(client, ctx, sku, peso_kg=peso, volumen_m3=volumen)


@then(
    re_(
        r"la pestaña Inventario de {} muestra peso (?P<peso>[\d.]+) kg y volumen "
        r"(?P<volumen>[\d.]+) m³",
        "sku",
    )
)
def inventario_muestra(client, ctx, sku, peso, volumen):
    p = producto(ctx, sku)
    assert (p.peso_kg, p.volumen_m3) == (Decimal(peso), Decimal(volumen))
    html = abrir_ficha(client, ctx, sku)
    assert 'name="peso_kg"' in html and tiene_pestana(html, "Inventario")


@then(re_("no veo los campos {} ni {}", "a", "b"))
def no_veo_campos(ctx, a, b):
    assert a not in ctx["ficha"] and b not in ctx["ficha"]


@when(re_(r"registro en {} una vida útil de (?P<dias>\d+) días", "sku"))
def registro_vida_util(client, ctx, sku, dias):
    post_ficha(client, ctx, sku, vida_util_dias=dias)
    assert producto(ctx, sku).vida_util_dias == int(dias)


@then(
    re_(
        r"un ingreso de {} el (?P<fecha>[\d-]+) sugiere el vencimiento (?P<vence>[\d-]+)",
        "sku",
    )
)
def ingreso_sugiere(ctx, sku, fecha, vence):
    dias = producto(ctx, sku).vida_util_dias
    assert date.fromisoformat(fecha) + timedelta(days=dias) == date.fromisoformat(vence)
    ctx["pendientes"].append("el ingreso con lote y vencimiento sugerido llega con 0003a")


@when(re_("creo el bien {} que se fabrica sin receta", "sku"))
def creo_granel_sin_receta(client, ctx, sku):
    datos = {"se_compra": None, "se_fabrica": "on", "unidad": "L"}
    post_producto(client, ctx, sku=sku, nombre=sku, **datos)


@when(re_(r"le agrego la receta con un componente {} (?P<q>[\d.]+) por litro", "componente"))
def agrego_receta(client, ctx, componente, q):
    crear_directo(ctx, componente)
    granel = Producto.all_tenants.filter(empresa=ctx["empresa"]).latest("id")
    granel = Producto.all_tenants.filter(empresa=ctx["empresa"], se_fabrica=True).latest("id")
    post_ficha(client, ctx, granel.sku, componente_0=producto(ctx, componente).id, cantidad_0=q)


@when(re_("intento eliminar {}", "sku"))
def intento_eliminar_sku(client, ctx, sku):
    post_estado(client, ctx, sku, "eliminar")


@when(re_("intento desactivar {}", "sku"))
def intento_desactivar_sku(client, ctx, sku):
    post_estado(client, ctx, sku, "desactivar")


@then(re_("{} queda inactivo y sigue en la receta de {}", "sku", "producto_"))
def inactivo_en_receta(ctx, sku, producto_):
    assert not producto(ctx, sku).activo
    receta = RecetaComponente.objects.filter(producto=producto(ctx, producto_))
    assert receta.filter(componente=producto(ctx, sku)).exists()
