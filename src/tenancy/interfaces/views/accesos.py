"""Pantallas de usuarios y roles de la empresa (spec 0001c, plan §5)."""

from django.contrib import messages
from django.db.models import Count
from django.shortcuts import redirect, render
from django.utils import timezone

from shared.domain.accesos import CATALOGO, MODULOS
from shared.domain.errores import AccesoDenegado, DomainError, NoEncontrado
from tenancy.application import roles as uc_roles
from tenancy.application import usuarios as uc_usuarios
from tenancy.domain.permisos import (
    NO_DISPONIBLE,
    agrupar_por_modulo,
    origen_permisos,
    permisos_habilitados,
)
from tenancy.infrastructure.contenedor import caso_de_uso, tenancy_service
from tenancy.infrastructure.models import Rol, Usuario
from tenancy.infrastructure.repositorios import roles_de_usuario
from tenancy.interfaces.acceso import requiere


def _intentar(request, accion) -> bool:
    """Ejecuta la acción; un error de negocio se muestra al usuario. 403/404 siguen de largo."""
    try:
        accion()
        return True
    except (AccesoDenegado, NoEncontrado):
        raise
    except DomainError as e:
        messages.error(request, e.mensaje)
        return False


def _ids(request, campo="roles") -> list[int]:
    return [int(i) for i in request.POST.getlist(campo)]


def _roles_de_empresa():
    return Rol.objects.order_by("-es_sistema", "nombre")


# --- Usuarios (UC-TEN-03) ---


@requiere("core.usuario.gestionar")
def usuarios(request):
    actor, hoy = request.actor, timezone.localdate()
    if request.method == "POST":
        p = request.POST
        crear = caso_de_uso(uc_usuarios.CrearUsuario)
        if _intentar(
            request,
            lambda: crear.ejecutar(
                actor,
                p.get("nombre", ""),
                p.get("email", ""),
                p.get("password", ""),
                _ids(request),
                hoy,
            ),
        ):
            messages.success(request, "Usuario creado.")
            return redirect("usuarios")
    filas = (
        Usuario.objects.filter(empresa_id=actor.empresa_id)
        .prefetch_related("roles")
        .order_by("-is_active", "nombre")
    )
    return render(
        request, "tenancy/usuarios.html", {"usuarios": filas, "roles": _roles_de_empresa()}
    )


@requiere("core.usuario.gestionar")
def usuario(request, usuario_id):
    actor, hoy = request.actor, timezone.localdate()
    ficha = Usuario.objects.filter(empresa_id=actor.empresa_id, pk=usuario_id).first()
    if ficha is None:
        raise NoEncontrado("No encontrado")
    if request.method == "POST":
        accion = request.POST.get("accion")
        if accion == "roles":
            caso = caso_de_uso(uc_usuarios.AsignarRoles)
            ok = _intentar(request, lambda: caso.ejecutar(actor, ficha.id, _ids(request), hoy))
        elif accion == "estado":
            caso = caso_de_uso(uc_usuarios.CambiarEstadoUsuario)
            activar = request.POST.get("activo") == "1"
            ok = _intentar(request, lambda: caso.ejecutar(actor, ficha.id, activar))
        else:
            caso = caso_de_uso(uc_usuarios.EditarUsuario)
            ok = _intentar(request, lambda: caso.ejecutar(actor, ficha.id, request.POST["nombre"]))
        if ok:
            messages.success(request, "Cambio guardado.")
            return redirect("usuario", usuario_id=ficha.id)
    origen = origen_permisos(
        roles_de_usuario(ficha.id), tenancy_service().habilitaciones_de(actor.empresa_id, hoy)
    )
    efectivos = agrupar_por_modulo(p for p, o in origen.items() if o != NO_DISPONIBLE)
    contexto = {
        "ficha": ficha,
        "roles": _roles_de_empresa(),
        "asignados": set(ficha.roles.values_list("id", flat=True)),
        "efectivos": {m: [(p, ", ".join(origen[p])) for p in ps] for m, ps in efectivos.items()},
        "no_disponibles": sorted(p for p, o in origen.items() if o == NO_DISPONIBLE),
    }
    return render(request, "tenancy/usuario.html", contexto)


# --- Roles (UC-TEN-09) ---


@requiere("core.rol.gestionar")
def roles(request):
    filas = _roles_de_empresa().annotate(n_usuarios=Count("usuarios"))
    return render(request, "tenancy/roles.html", {"roles": filas})


def _matriz(habilitados, marcados):
    """Módulo → funcionalidad → permisos; lo no habilitado queda bloqueado (RF-TEN-35, 39)."""
    return [
        {
            "nombre": nombre,
            "funcionalidades": [
                {
                    "nombre": f.nombre,
                    "habilitada": bool(set(f.permisos) & habilitados),
                    "permisos": [
                        {"codigo": p, "marcado": p in marcados, "habilitado": p in habilitados}
                        for p in f.permisos
                    ],
                }
                for f in CATALOGO.values()
                if f.modulo == modulo
            ],
        }
        for modulo, nombre in MODULOS.items()
    ]


@requiere("core.rol.gestionar")
def rol(request, rol_id=None):
    actor, hoy = request.actor, timezone.localdate()
    rol = None
    if rol_id is not None:
        rol = Rol.objects.filter(pk=rol_id).first()
        if rol is None:
            raise NoEncontrado("No encontrado")
    if request.method == "POST":
        p = request.POST
        accion, permisos = p.get("accion", "guardar"), set(p.getlist("permisos"))
        if rol is None:
            caso = caso_de_uso(uc_roles.CrearRol)
            nuevo = {}
            ok = _intentar(
                request, lambda: nuevo.update(id=caso.ejecutar(actor, p["nombre"], permisos, hoy))
            )
            if ok:
                messages.success(request, "Rol creado.")
                return redirect("rol", rol_id=nuevo["id"])
        else:
            acciones = {
                "guardar": lambda: caso_de_uso(uc_roles.EditarRol).ejecutar(
                    actor, rol.id, p["nombre"], permisos, hoy
                ),
                "duplicar": lambda: caso_de_uso(uc_roles.DuplicarRol).ejecutar(
                    actor, rol.id, p.get("nombre_copia") or f"{rol.nombre} (copia)", hoy
                ),
                "desactivar": lambda: caso_de_uso(uc_roles.CambiarEstadoRol).ejecutar(
                    actor, rol.id, False
                ),
                "activar": lambda: caso_de_uso(uc_roles.CambiarEstadoRol).ejecutar(
                    actor, rol.id, True
                ),
                "eliminar": lambda: caso_de_uso(uc_roles.EliminarRol).ejecutar(actor, rol.id),
            }
            if _intentar(request, acciones.get(accion, acciones["guardar"])):
                messages.success(request, "Cambio guardado.")
                if accion in ("eliminar", "duplicar"):
                    return redirect("roles")
                return redirect("rol", rol_id=rol.id)
    habilitados = permisos_habilitados(tenancy_service().habilitaciones_de(actor.empresa_id, hoy))
    marcados = set(rol.permisos.values_list("permiso", flat=True)) if rol else set()
    if rol and rol.es_sistema:
        marcados = set(habilitados)
    contexto = {"rol": rol, "matriz": _matriz(habilitados, marcados)}
    return render(request, "tenancy/rol.html", contexto)
