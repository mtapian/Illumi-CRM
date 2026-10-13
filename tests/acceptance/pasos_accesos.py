"""Pasos de roles_permisos.feature y usuarios.feature (0001c).

"Puede <acción>" se verifica con el `Actor` del usuario: es el mismo control que hace cada
caso de uso en el servidor (meta-test de autorización). Lo que necesita pantallas de otras
specs (stock, productos, compras) queda como pendiente con su motivo.
"""

import re
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.test import Client
from django.utils import timezone
from pytest_bdd import given, parsers, then, when

from shared.domain.accesos import CATALOGO, MODULOS, PERMISOS, requeridas
from shared.domain.errores import AccesoDenegado, FuncionalidadNoDisponible
from shared.domain.tenant import tenant_context
from tenancy.domain.permisos import permisos_habilitados
from tenancy.infrastructure.contenedor import actor_de, plataforma, sembrador_roles
from tenancy.infrastructure.models import PlanFuncionalidad, Rol, Usuario, UsuarioRol
from tenancy.infrastructure.repositorios import RolesOrm
from tests.acceptance.conftest import contenido
from tests.acceptance.pasos_sesion import (
    crear_empresa,
    crear_usuario,
    empresa_por_nombre,
    iniciar_sesion,
)

BACKEND = "tenancy.infrastructure.auth_backend.EmailBackend"
Q = r'"(?P<{}>[^"]+)"'

ACCIONES = {
    "registrar una venta": "ventas.venta.registrar",
    "anular una venta": "ventas.venta.anular",
    "ver el estado de resultados": "finanzas.resultados.ver",
    "iniciar una OP": "produccion.op.ejecutar",
    "planificar una OP": "produccion.op.planificar",
    "registrar una compra": "compras.compra.registrar",
    "anular una compra": "compras.compra.anular",
    "registrar un ajuste": "inventario.ajuste.registrar",
    "registrar un ajuste de inventario": "inventario.ajuste.registrar",
    "registrar ajustes": "inventario.ajuste.registrar",
    "crear un usuario": "core.usuario.gestionar",
    "generar un token de API": "api.token.gestionar",
}
MODULO_POR_NOMBRE = {nombre.lower(): codigo for codigo, nombre in MODULOS.items()}


def re_(texto: str, *nombres: str):
    return parsers.re(texto.format(*(Q.format(n) for n in nombres)))


def por_nombre(nombre: str) -> str:
    return next(c for c, f in CATALOGO.items() if f.nombre == nombre)


def hoy() -> date:
    return timezone.localdate()


def usuario(email: str) -> Usuario:
    return Usuario.objects.get(email=email)


def como(client, email: str):
    client.force_login(usuario(email), BACKEND)
    return client


def actor(email: str):
    return actor_de(usuario(email), hoy())


def rol_id(empresa, nombre: str) -> int:
    return Rol.all_tenants.get(empresa=empresa, nombre=nombre).id


def crear_rol(empresa, nombre: str, permisos) -> int:
    existente = Rol.all_tenants.filter(empresa=empresa, nombre=nombre).first()
    if existente:
        return existente.id
    return RolesOrm().crear_rol(empresa.id, nombre, set(permisos))


def usuario_con_roles(email: str, empresa, *ids: int) -> Usuario:
    u = Usuario.objects.filter(email=email).first() or crear_usuario(email, empresa, rol=None)
    for i in ids:
        UsuarioRol.objects.get_or_create(usuario=u, rol_id=i)
    return u


def puede(email: str, accion: str) -> bool:
    if accion.startswith("iniciar sesión en "):
        return iniciar_sesion(Client(), email).redirect_chain[-1][0] == "/dashboard/"
    if accion.startswith("acceder al módulo de "):
        modulo = MODULO_POR_NOMBRE[accion.removeprefix("acceder al módulo de ")]
        return any(CATALOGO[PERMISOS[p]].modulo == modulo for p in actor(email).permisos)
    return actor(email).puede(ACCIONES[accion])


# --- Antecedentes de roles_permisos.feature ---


@given(re_("la empresa {} con las funcionalidades habilitadas:", "nombre"))
def empresa_con_funcionalidades(ctx, nombre, datatable):
    ctx["empresa"] = crear_empresa(nombre)
    for fila in datatable[1:]:
        PlanFuncionalidad.objects.create(
            plan=ctx["empresa"].plan, funcionalidad_id=por_nombre(fila[1])
        )


@given(re_("la funcionalidad {} no está habilitada para {}", "funcionalidad", "nombre"))
def no_habilitada(ctx, funcionalidad, nombre):
    assert por_nombre(funcionalidad) not in plataforma().habilitadas(ctx["empresa"].id, hoy())


@given(re_("{} tiene el rol {}", "email", "rol"))
def tiene_el_rol(ctx, email, rol):
    crear_usuario(email, ctx["empresa"], rol)


# --- Roles (UC-TEN-09) ---


@when(re_("se registra la empresa {}", "nombre"))
def se_registra(ctx, nombre):
    # El registro completo se prueba en 0001a; aquí, el sembrador que corre al registrar,
    # con las habilitaciones del plan de los antecedentes.
    nueva = crear_empresa(nombre)
    nueva.plan = ctx["empresa"].plan
    nueva.save()
    admin = crear_usuario("admin@nueva.pe", nueva, rol=None)
    sembrador_roles()(nueva.id, admin.id, hoy())
    ctx["registrada"] = nueva


@then(parsers.re(r"existen los roles (?P<lista>.+)"))
def existen_los_roles(ctx, lista):
    roles = {r.nombre: r for r in Rol.all_tenants.filter(empresa=ctx["registrada"])}
    assert set(roles) == set(re.findall(r'"([^"]+)"', lista))
    assert roles["Administrador"].es_sistema


@then("los roles editables solo contienen permisos de funcionalidades habilitadas")
def roles_editables_recortados(ctx):
    habilitados = permisos_habilitados(plataforma().habilitadas(ctx["registrada"].id, hoy()))
    for rol in Rol.all_tenants.filter(empresa=ctx["registrada"], es_sistema=False):
        assert set(rol.permisos.values_list("permiso", flat=True)) <= habilitados, rol


@when(re_("{} crea el rol {} con los permisos:", "email", "nombre"))
def crea_rol(client, ctx, email, nombre, datatable):
    permisos = [fila[0] for fila in datatable[1:]]
    como(client, email).post("/roles/nuevo/", {"nombre": nombre, "permisos": permisos})


@then(re_(r"el rol {} queda activo con (?P<n>\d+) permisos", "nombre"))
def rol_activo_con(ctx, nombre, n):
    rol = Rol.all_tenants.get(empresa=ctx["empresa"], nombre=nombre)
    assert rol.activo and rol.permisos.count() == int(n)


@when(re_("{} abre el editor del rol {}", "email", "nombre"))
def abre_editor(client, ctx, email, nombre):
    ctx["pagina"] = contenido(como(client, email).get(f"/roles/{rol_id(ctx['empresa'], nombre)}/"))


@then(re_("la funcionalidad {} aparece bloqueada con la etiqueta {}", "funcionalidad", "etiqueta"))
def aparece_bloqueada(ctx, funcionalidad, etiqueta):
    patron = (
        rf'class="funcionalidad bloqueada">\s*'
        rf'<strong>{funcionalidad}</strong> <span class="chip">{etiqueta}'
    )
    assert re.search(patron, ctx["pagina"])


@when(
    re_(
        "{} envía el rol {} con el permiso {} manipulando el formulario",
        "email",
        "nombre",
        "permiso",
    )
)
def envia_manipulado(client, ctx, email, nombre, permiso):
    rol = Rol.all_tenants.get(empresa=ctx["empresa"], nombre=nombre)
    permisos = [*rol.permisos.values_list("permiso", flat=True), permiso]
    ctx["respuesta"] = como(client, email).post(
        f"/roles/{rol.id}/", {"nombre": nombre, "permisos": permisos}, follow=True
    )


@then(re_("la operación es rechazada con el mensaje {}", "mensaje"))
def rechazada(ctx, mensaje):
    for respuesta in ctx.get("respuestas") or [ctx["respuesta"]]:
        assert mensaje in contenido(respuesta)


@given(re_("el rol {} con {}$", "nombre", "permiso"))
def rol_con(ctx, nombre, permiso):
    ctx.setdefault("roles", []).append(crear_rol(ctx["empresa"], nombre, {permiso}))


@when(re_("{} asigna ambos roles a {}", "admin", "email"))
def asigna_ambos(client, ctx, admin, email):
    ana = usuario_con_roles(email, ctx["empresa"])
    como(client, admin).post(f"/usuarios/{ana.id}/", {"accion": "roles", "roles": ctx["roles"]})


@then(parsers.re(r'"(?P<email>[^"]+)" puede (?P<accion>.+?)(?: sin cambios en sus roles)?$'))
def puede_hacer(email, accion):
    assert puede(email, accion), accion


@then(parsers.re(r'"(?P<email>[^"]+)" no puede (?P<accion>.+)$'))
def no_puede_hacer(email, accion):
    if accion == "iniciar sesión":
        assert "desactivado" in contenido(iniciar_sesion(Client(), email))
        return
    assert not puede(email, accion), accion


@given(re_("el rol {} con {} asignado a {}", "nombre", "permiso", "email"))
def rol_con_asignado(ctx, nombre, permiso, email):
    usuario_con_roles(email, ctx["empresa"], crear_rol(ctx["empresa"], nombre, {permiso}))


@when(re_("el super admin quita a {} la funcionalidad {}", "nombre", "funcionalidad"))
def super_quita(ctx, nombre, funcionalidad):
    funcs = [por_nombre(funcionalidad)]
    plataforma().quitar(ctx["empresa"].id, funcs, "Pedido", None, None, hoy(), True)


@then(re_("{} no puede registrar ajustes desde su siguiente acción", "email"))
def no_puede_registrar_ajustes(email):
    try:
        actor(email).exige("inventario.ajuste.registrar")
        raise AssertionError("debió rechazarse")
    except FuncionalidadNoDisponible as e:
        assert e.mensaje == "Esta funcionalidad ya no está disponible en tu plan"


@then(re_("el menú de {} ya no muestra {}", "email", "texto"))
def menu_no_muestra(client, ctx, email, texto):
    pagina = contenido(como(client, email).get("/dashboard/"))
    assert texto not in pagina.split('<nav class="menu-lateral">')[1].split("</nav>")[0]
    ctx["pendientes"].append("la opción de menú de ajustes llega con 0003b")


@then(re_("el rol {} conserva el permiso marcado como {}", "nombre", "etiqueta"))
def conserva_marcado(client, ctx, nombre, etiqueta):
    pagina = contenido(
        como(client, "lucia@andina.pe").get(f"/roles/{rol_id(ctx['empresa'], nombre)}/")
    )
    assert re.search(r'value="inventario.ajuste.registrar" checked disabled>.*?' + etiqueta, pagina)


@when(re_("el super admin vuelve a agregar {}", "funcionalidad"))
def super_vuelve_a_agregar(ctx, funcionalidad):
    funcs = [por_nombre(funcionalidad)]
    plataforma().agregar(ctx["empresa"].id, funcs, "Rehabilitar", None, None, hoy())


@then(re_("{} vuelve a poder registrar ajustes sin que nadie edite su rol", "email"))
def vuelve_a_poder(email):
    assert actor(email).puede("inventario.ajuste.registrar")


@when(re_("el super admin agrega a {} la funcionalidad {}", "nombre", "funcionalidad"))
def super_agrega(ctx, nombre, funcionalidad):
    # RN-TEN-09: una funcionalidad se agrega junto con las que requiere.
    codigo = por_nombre(funcionalidad)
    funcs = [codigo, *requeridas(codigo)]
    plataforma().agregar(ctx["empresa"].id, funcs, "Piloto", None, None, hoy())


@when(re_('{} intenta editar o eliminar el rol "Administrador"', "email"))
def intenta_editar_admin(client, ctx, email):
    url = f"/roles/{rol_id(ctx['empresa'], 'Administrador')}/"
    ctx["pagina"] = contenido(como(client, email).get(url))
    ctx["respuestas"] = [
        client.post(url, {"accion": "eliminar"}, follow=True),
        client.post(url, {"accion": "guardar", "nombre": "X", "permisos": []}, follow=True),
    ]


@then("la operación no está disponible")
def no_disponible(ctx):
    assert 'value="eliminar"' not in ctx["pagina"] and 'value="guardar"' not in ctx["pagina"]
    for respuesta in ctx["respuestas"]:
        assert "El rol Administrador no se puede editar ni eliminar" in contenido(respuesta)
    assert Rol.all_tenants.filter(empresa=ctx["empresa"], nombre="Administrador").exists()


@given(re_(r"el rol {} asignado a (?P<n>\d+) usuarios", "nombre"))
def rol_asignado_a(ctx, nombre, n):
    rol = crear_rol(ctx["empresa"], nombre, {"ventas.venta.registrar"})
    ctx["rol"], ctx["usuarios_rol"] = rol, [f"u{i}@andina.pe" for i in range(int(n))]
    for email in ctx["usuarios_rol"]:
        usuario_con_roles(email, ctx["empresa"], rol)


@when(re_("{} intenta eliminar {}", "email", "nombre"))
def intenta_eliminar(client, ctx, email, nombre):
    ctx["respuesta"] = como(client, email).post(
        f"/roles/{ctx['rol']}/", {"accion": "eliminar"}, follow=True
    )


@when("lo desactiva")
def lo_desactiva(client, ctx):
    client.post(f"/roles/{ctx['rol']}/", {"accion": "desactivar"})


@then("esos usuarios pierden los permisos del rol desde su siguiente acción")
def pierden_permisos(ctx):
    for email in ctx["usuarios_rol"]:
        assert not actor(email).puede("ventas.venta.registrar")


@given(re_("el rol propio {} con únicamente los permisos {} y {}", "nombre", "p1", "p2"))
def rol_propio(ctx, nombre, p1, p2):
    # Creado cuando PRODUCCION estaba habilitado: el rol conserva sus permisos (RF-TEN-39).
    ctx["rol"] = crear_rol(ctx["empresa"], nombre, {p1, p2})


@given(
    re_(
        "que {} solo tiene el rol {} y la empresa no tiene habilitado PRODUCCION", "email", "nombre"
    )
)
def solo_tiene_rol(ctx, email, nombre):
    usuario_con_roles(email, ctx["empresa"], ctx["rol"])
    assert not {"produccion.op"} & plataforma().habilitadas(ctx["empresa"].id, hoy())


@when(re_("{} inicia sesión$", "email"))
def inicia_sesion(client, ctx, email):
    ctx["respuesta"] = iniciar_sesion(client, email)


@then(re_("ve el mensaje {}", "texto"))
def ve_mensaje(ctx, texto):
    assert texto in contenido(ctx["respuesta"])


@given(re_("{} con los roles {} e {}", "email", "r1", "r2"))
def con_los_roles(ctx, email, r1, r2):
    vendedor = crear_rol(ctx["empresa"], r1, {"ventas.venta.registrar", "ventas.cliente.ver"})
    inventarista = crear_rol(ctx["empresa"], r2, {"inventario.ajuste.registrar"})
    usuario_con_roles(email, ctx["empresa"], vendedor, inventarista)


@when(re_("{} abre la ficha de {}", "admin", "email"))
def abre_ficha(client, ctx, admin, email):
    ctx["pagina"] = contenido(como(client, admin).get(f"/usuarios/{usuario(email).id}/"))


@then("ve sus permisos efectivos agrupados por módulo con el rol de origen de cada uno")
def ve_permisos_agrupados(ctx):
    pagina = ctx["pagina"]
    ventas = pagina.index("<h3>Ventas</h3>")
    inventario = pagina.index("<h3>Inventario</h3>")
    assert re.search(r"ventas.venta.registrar</code></td><td>Vendedor taproom", pagina[ventas:])
    assert re.search(
        r"inventario.ajuste.registrar</code></td><td>Inventarista", pagina[inventario:ventas]
    )


@given(re_("el rol {} sin {} asignado a {}", "nombre", "permiso", "email"))
def rol_sin(ctx, nombre, permiso, email):
    rol = crear_rol(ctx["empresa"], nombre, {"inventario.stock.ver", "inventario.lote.ver"})
    usuario_con_roles(email, ctx["empresa"], rol)
    assert not actor(email).puede(permiso)


@when(re_("{} consulta el stock", "email"))
def consulta_stock(client, ctx, email):
    """Con un producto con stock en un lote, a costo 4.25 (pantalla de 0003c)."""
    from catalog.infrastructure.models import Producto, Unidad
    from inventory.application.servicio import Linea
    from inventory.infrastructure.contenedor import inventario
    from inventory.infrastructure.models import Almacen

    with tenant_context(ctx["empresa"].id), transaction.atomic():
        und = Unidad.objects.get_or_create(
            abreviatura="UND", defaults={"nombre": "Unidad", "codigo_sunat": "NIU"}
        )[0]
        p = Producto.objects.create(sku="ENV-TAPA", nombre="Tapa corona", unidad=und)
        principal = Almacen.objects.get_or_create(nombre="Principal")[0]
        linea = Linea(p.id, principal.id, Decimal("120"), Decimal("4.25"), "T-01")
        inventario().registrar_entrada("SALDO_INICIAL", "AJUSTE", 1, [linea], None, hoy())
    ctx["pagina"] = como(client, email).get("/inventario/stock/").content.decode()


@then("ve cantidades por producto y lote")
def ve_cantidades(ctx):
    assert "ENV-TAPA" in ctx["pagina"] and "120 UND" in ctx["pagina"]
    assert "lote T-01" in ctx["pagina"]


@then("no ve costo promedio ni valorización")
def no_ve_costos(ctx):
    assert "4.25" not in ctx["pagina"] and "Valorización" not in ctx["pagina"]
    assert not actor("ana@andina.pe").puede("inventario.costo.ver")


@given(re_("el usuario {} sin el permiso {}", "email", "permiso"))
def usuario_sin_permiso(ctx, email, permiso):
    crear_usuario(email, ctx["empresa"], "Ventas")
    ctx["email"] = email
    assert not actor(email).puede(permiso)


@when(re_("invoca directamente la acción {}", "accion"))
def invoca_directamente(client, ctx, accion):
    ctx["usuarios_antes"] = Usuario.objects.count()
    if accion == "crear un usuario":
        ctx["respuesta"] = como(client, ctx["email"]).post(
            "/usuarios/", {"nombre": "X", "email": "x@andina.pe", "password": "x"}
        )
        return
    if accion == "registrar una compra":
        ctx["respuesta"] = como(client, ctx["email"]).post("/compras/nueva/", {})
        return
    if accion == "generar un token de API":
        ctx["respuesta"] = como(client, ctx["email"]).post(
            "/integracion/tokens/", {"accion": "crear", "nombre": "x", "tecnico": "n8n"}
        )
        return
    try:
        actor(ctx["email"]).exige(ACCIONES[accion])
    except AccesoDenegado as e:
        ctx["denegado"] = e.mensaje
    ctx["pendientes"].append(f'la acción "{accion}" llega con su spec; se verificó el permiso')


@then('recibe "Acceso denegado"')
def recibe_acceso_denegado(ctx):
    if "respuesta" in ctx:
        assert ctx["respuesta"].status_code == 403
        assert "Acceso denegado" in contenido(ctx["respuesta"])
    else:
        assert ctx["denegado"] == "Acceso denegado"


@then("la acción no se ejecuta")
def no_se_ejecuta(ctx):
    assert Usuario.objects.count() == ctx["usuarios_antes"]


# --- usuarios.feature (UC-TEN-03) ---


@when(re_("{} crea el usuario {} con el rol {}", "admin", "email", "rol"))
def crea_usuario(client, ctx, admin, email, rol):
    como(client, admin).post(
        "/usuarios/",
        {
            "nombre": email,
            "email": email,
            "password": "Clave-Segura-2026",
            "roles": [rol_id(ctx["empresa"], rol)],
        },
    )


@given(re_(r"que el plan de {} se cambia a uno que permite (?P<n>\d+) usuarios", "nombre"))
def plan_permite(nombre, n):
    plan = empresa_por_nombre(nombre).plan
    plan.limite_usuarios = int(n)
    plan.save()


@given(re_(r"{} tiene (?P<n>\d+) usuarios activos", "nombre"))
def tiene_n_usuarios(nombre, n):
    e = empresa_por_nombre(nombre)
    for i in range(int(n) - Usuario.objects.filter(empresa=e, is_active=True).count()):
        crear_usuario(f"extra{i}@andina.pe", e, "Ventas")


@when(re_("{} intenta crear el usuario {}", "admin", "email"))
def intenta_crear(client, ctx, admin, email):
    ctx["respuesta"] = como(client, admin).post(
        "/usuarios/", {"nombre": email, "email": email, "password": "x"}, follow=True
    )


@given(re_('que {} es el único usuario activo con el rol "Administrador"', "email"))
def unico_admin(ctx, email):
    admin = rol_id(ctx["empresa"], "Administrador")
    assert list(
        UsuarioRol.objects.filter(rol_id=admin, usuario__is_active=True).values_list(
            "usuario__email", flat=True
        )
    ) == [email]


@when(re_('{} intenta desactivarse o quitarse el rol "Administrador"', "email"))
def intenta_desactivarse(client, ctx, email):
    url = f"/usuarios/{usuario(email).id}/"
    como(client, email)
    ctx["respuestas"] = [
        client.post(url, {"accion": "estado", "activo": "0"}, follow=True),
        client.post(url, {"accion": "roles", "roles": []}, follow=True),
    ]


@given(re_("el usuario {} con el rol {} en {}", "email", "rol", "nombre"))
def usuario_con_rol_en(ctx, email, rol, nombre):
    crear_usuario(email, empresa_por_nombre(nombre), rol)
    ctx["email"] = email


@when(re_("intenta {}$", "accion"))
def intenta_accion(ctx, accion):
    ctx["accion"] = accion


@then(re_("el resultado es {}", "resultado"))
def resultado(ctx, resultado):
    assert puede(ctx["email"], ctx["accion"]) == (resultado == "permitido")


@given(re_("que {} tiene el producto {}", "nombre", "producto"))
def tiene_producto(ctx, nombre, producto):
    ctx["pendientes"].append("productos llegan con 0002a; el aislamiento se prueba en tests/meta")


@when(re_("{} busca productos", "email"))
def busca_productos(email):
    pass


@then(re_("no ve el producto {}", "producto"))
def no_ve_producto(producto):
    pass


@then(parsers.parse('si intenta abrir ese producto por su identificador recibe "No encontrado"'))
def abrir_producto_ajeno():
    pass


@given(re_("el usuario {} con el rol {} y el permiso {}", "email", "rol", "permiso"))
def usuario_rol_y_permiso(ctx, email, rol, permiso):
    extra = crear_rol(ctx["empresa"], "Gestor de usuarios", {permiso})
    usuario_con_roles(email, ctx["empresa"], rol_id(ctx["empresa"], rol), extra)


@when(re_("{} intenta asignarse el rol {}", "email", "rol"))
def intenta_asignarse(client, ctx, email, rol):
    jose = usuario(email)
    roles = [*UsuarioRol.objects.filter(usuario=jose).values_list("rol_id", flat=True)]
    roles.append(rol_id(ctx["empresa"], rol))
    ctx["respuesta"] = como(client, email).post(
        f"/usuarios/{jose.id}/", {"accion": "roles", "roles": roles}, follow=True
    )


@when(re_("{} intenta asignar a {} un rol con {}", "email", "otro", "permiso"))
def intenta_asignar_rol_con(client, ctx, email, otro, permiso):
    rol = crear_rol(ctx["empresa"], "Gestor de roles", {permiso})
    ana = usuario_con_roles(otro, ctx["empresa"])
    ctx["respuesta"] = como(client, email).post(
        f"/usuarios/{ana.id}/", {"accion": "roles", "roles": [rol]}, follow=True
    )


@given(re_("que {} registró la compra {}", "email", "compra"))
def registro_compra(ctx, email, compra):
    from inventory.infrastructure.models import Almacen
    from purchasing.infrastructure.models import Compra, Proveedor

    empresa = empresa_por_nombre("Cervecería Andina")
    autor = crear_usuario(email, empresa, "Producción")
    proveedor = Proveedor.all_tenants.create(
        empresa=empresa, tipo_doc="DNI", num_doc="45678912", razon_social="Juan Pérez"
    )
    ctx["compra"] = Compra.all_tenants.create(
        empresa=empresa,
        numero=int(compra.removeprefix("C-")),
        proveedor=proveedor,
        fecha=date.today(),
        almacen=Almacen.all_tenants.get_or_create(empresa=empresa, nombre="Principal")[0],
        doc_tipo="SIN_DOCUMENTO",
        igv_pct=18,
        usuario=autor,
    ).id


@when(re_("{} desactiva a {}", "admin", "email"))
def desactiva(client, ctx, admin, email):
    url = f"/usuarios/{usuario(email).id}/"
    como(client, admin).post(url, {"accion": "estado", "activo": "0"})
    ctx["pagina"] = contenido(client.get(url))


@then(re_("la compra {} sigue mostrando a {} como autor", "compra", "email"))
def compra_con_autor(client, ctx, compra, email):
    assert Usuario.objects.filter(email=email).exists()  # no se borró
    pagina = contenido(como(client, "lucia@andina.pe").get(f"/compras/{ctx['compra']}/"))
    assert compra in pagina and f"Registrada por {email}" in pagina


@then("no existe la opción de eliminar usuarios")
def sin_eliminar_usuarios(ctx):
    assert "Eliminar" not in ctx["pagina"]
