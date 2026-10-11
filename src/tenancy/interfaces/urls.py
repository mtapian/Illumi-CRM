from django.urls import path

from shared.interfaces.menu import menu
from tenancy.interfaces import auth
from tenancy.interfaces.views import (
    accesos,
    auditoria_tokens,
    empresa,
    inicio,
    plataforma,
    recuperacion,
    registro,
    suscripcion,
)

urlpatterns = [
    path("registro/", registro.registro, name="registro"),
    path("login/", auth.iniciar_sesion, name="login"),
    path("logout/", auth.cerrar_sesion, name="logout"),
    path("password-reset/", recuperacion.pedir_enlace, name="password_reset"),
    path(
        "password-reset/<uidb64>/<token>/",
        recuperacion.definir_contrasena,
        name="password_reset_confirm",
    ),
    path("dashboard/", inicio.dashboard, name="dashboard"),
    path("configuracion/empresa/", empresa.configurar_empresa, name="configurar_empresa"),
    path("suscripcion/", suscripcion.suscripcion, name="suscripcion"),
    path("usuarios/", accesos.usuarios, name="usuarios"),
    path("usuarios/<int:usuario_id>/", accesos.usuario, name="usuario"),
    path("roles/", accesos.roles, name="roles"),
    path("roles/nuevo/", accesos.rol, name="rol_nuevo"),
    path("roles/<int:rol_id>/", accesos.rol, name="rol"),
    path("auditoria/accesos/", auditoria_tokens.auditoria, name="auditoria"),
    path("integracion/tokens/", auditoria_tokens.tokens, name="tokens"),
    path("plataforma/", plataforma.empresas, name="plataforma"),
    path("plataforma/empresas/", plataforma.empresas, name="plataforma_empresas"),
    path("plataforma/empresas/<int:empresa_id>/", plataforma.empresa, name="plataforma_empresa"),
    path(
        "plataforma/empresas/<int:empresa_id>/modulos/",
        plataforma.modulos,
        name="plataforma_modulos",
    ),
    path("plataforma/planes/", plataforma.planes, name="plataforma_planes"),
    path("plataforma/planes/<int:plan_id>/", plataforma.plan, name="plataforma_plan"),
]

menu.agregar(None, "Inicio", "/dashboard/", orden=0, icono="inicio")
CONFIG = "Configuración"
menu.agregar(
    CONFIG,
    "Empresa",
    "/configuracion/empresa/",
    900,
    permiso="core.empresa.gestionar",
    icono="empresa",
)
menu.agregar(
    CONFIG, "Usuarios", "/usuarios/", 910, permiso="core.usuario.gestionar", icono="usuarios"
)
menu.agregar(CONFIG, "Roles", "/roles/", 920, permiso="core.rol.gestionar", icono="roles")
menu.agregar(
    CONFIG, "Auditoría", "/auditoria/accesos/", 925, permiso="core.auditoria.ver", icono="auditoria"
)
menu.agregar(
    CONFIG,
    "Tokens de API",
    "/integracion/tokens/",
    928,
    permiso="api.token.gestionar",
    icono="token",
)
menu.agregar(
    CONFIG, "Suscripción", "/suscripcion/", 930, permiso="core.suscripcion.ver", icono="suscripcion"
)
menu.agregar(
    None, "Empresas", "/plataforma/empresas/", orden=0, ambito="plataforma", icono="empresa"
)
menu.agregar(None, "Planes", "/plataforma/planes/", orden=10, ambito="plataforma", icono="planes")
