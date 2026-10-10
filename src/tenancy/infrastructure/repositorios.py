import secrets
from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.text import slugify

from shared.domain.errores import NoEncontrado
from tenancy.domain.errores import EmailDuplicado, RucDuplicado
from tenancy.domain.habilitaciones import Ajuste
from tenancy.domain.permisos import Rol as RolDominio
from tenancy.domain.suscripcion import Estado
from tenancy.infrastructure.models import (
    Actividad,
    ApiToken,
    AuditoriaAcceso,
    Empresa,
    EmpresaAjuste,
    Funcionalidad,
    ParametroVigencia,
    Plan,
    PlanFuncionalidad,
    Rol,
    RolPermiso,
    Usuario,
    UsuarioRol,
)


class ParametrosOrm:
    def historial(self, clave: str, empresa_id: int | None) -> list[tuple[date, Decimal]]:
        filas = ParametroVigencia.objects.filter(clave=clave, empresa_id=empresa_id)
        return list(filas.values_list("vigente_desde", "valor"))

    def agregar(self, clave: str, empresa_id: int | None, valor: Decimal, desde: date) -> None:
        ParametroVigencia.objects.create(
            clave=clave, empresa_id=empresa_id, valor=valor, vigente_desde=desde
        )


class EmpresasOrm:
    def estado(self, empresa_id: int) -> tuple[Estado, date | None]:
        estado, fecha_termino = Empresa.objects.values_list("estado", "fecha_termino").get(
            pk=empresa_id
        )
        return Estado(estado), fecha_termino

    def actualizar(self, empresa_id: int, datos: dict) -> None:
        Empresa.objects.filter(pk=empresa_id).update(**datos)


class RegistroOrm:
    """Crea empresa y administrador; traduce las carreras de unicidad a errores de dominio."""

    def existe_ruc(self, ruc: str) -> bool:
        return Empresa.objects.filter(ruc=ruc).exists()

    def existe_email(self, email: str) -> bool:
        return Usuario.objects.filter(email__iexact=email).exists()

    def plan_de_prueba(self) -> tuple[int, int] | None:
        return (
            Plan.objects.filter(es_plan_prueba=True, activo=True)
            .values_list("id", "dias_prueba")
            .first()
        )

    def crear_empresa(self, ruc, razon_social, nombre_comercial, plan_id, fecha_termino) -> int:
        try:
            with transaction.atomic():
                return Empresa.objects.create(
                    ruc=ruc,
                    razon_social=razon_social,
                    nombre_comercial=nombre_comercial,
                    plan_id=plan_id,
                    estado=Estado.TRIAL,
                    fecha_termino=fecha_termino,
                ).id
        except IntegrityError as e:
            raise RucDuplicado("Ya existe una empresa con este RUC") from e

    def crear_usuario(self, empresa_id, nombre, email, password) -> int:
        try:
            with transaction.atomic():
                return Usuario.objects.create_user(
                    email, password, nombre=nombre, empresa_id=empresa_id
                ).id
        except IntegrityError as e:
            raise EmailDuplicado("Este email ya está registrado") from e


class HabilitacionesOrm:
    def funcionalidades_plan(self, empresa_id: int) -> set[str]:
        plan = Plan.objects.get(empresas_plan__id=empresa_id)
        if plan.es_plan_prueba:  # PRD Q8: el plan de prueba incluye todo
            return set(
                Funcionalidad.objects.filter(obsoleto=False).values_list("codigo", flat=True)
            )
        return funcionalidades_de_plan(plan.id)

    def ajustes(self, empresa_id: int) -> list[Ajuste]:
        filas = EmpresaAjuste.objects.filter(empresa_id=empresa_id, revocado_en__isnull=True)
        return [
            Ajuste(f, t, h)
            for f, t, h in filas.values_list("funcionalidad", "tipo", "vigente_hasta")
        ]


def funcionalidades_de_plan(plan_id: int) -> set[str]:
    return set(
        PlanFuncionalidad.objects.filter(plan_id=plan_id).values_list("funcionalidad", flat=True)
    )


class PlataformaOrm(HabilitacionesOrm):
    def estado(self, empresa_id: int) -> tuple[Estado, str]:
        estado, previo = (
            Empresa.objects.select_for_update()
            .values_list("estado", "estado_previo")
            .get(pk=empresa_id)
        )
        return Estado(estado), previo

    def actualizar_empresa(self, empresa_id: int, **campos) -> None:
        Empresa.objects.filter(pk=empresa_id).update(**campos)

    def registrar_actividad(self, empresa_id, actor_id, accion, motivo, detalle) -> None:
        Actividad.objects.create(
            empresa_id=empresa_id, actor_id=actor_id, accion=accion, motivo=motivo, detalle=detalle
        )

    def guardar_ajustes(self, empresa_id, funcionalidades, tipo, hasta, motivo, actor_id) -> None:
        EmpresaAjuste.objects.filter(
            empresa_id=empresa_id, funcionalidad__in=funcionalidades, revocado_en__isnull=True
        ).update(revocado_en=timezone.now())
        EmpresaAjuste.objects.bulk_create(
            EmpresaAjuste(
                empresa_id=empresa_id,
                funcionalidad_id=f,
                tipo=tipo,
                vigente_hasta=hasta,
                motivo=motivo,
                creado_por_id=actor_id,
            )
            for f in funcionalidades
        )

    def reemplazar_plan(self, plan_id, funcionalidades, limites) -> None:
        Plan.objects.filter(pk=plan_id).update(**limites)
        PlanFuncionalidad.objects.filter(plan_id=plan_id).delete()
        PlanFuncionalidad.objects.bulk_create(
            PlanFuncionalidad(plan_id=plan_id, funcionalidad_id=f) for f in funcionalidades
        )

    def empresas_con_plan(self, plan_id: int) -> int:
        return Empresa.objects.filter(plan_id=plan_id).count()


class RolesOrm:
    def crear_rol(self, empresa_id, nombre, permisos, es_sistema=False) -> int:
        rol = Rol.all_tenants.create(empresa_id=empresa_id, nombre=nombre, es_sistema=es_sistema)
        RolPermiso.objects.bulk_create(RolPermiso(rol=rol, permiso_id=p) for p in permisos)
        return rol.id

    def asignar_roles(self, usuario_id, rol_ids) -> None:
        UsuarioRol.objects.filter(usuario_id=usuario_id).delete()
        UsuarioRol.objects.bulk_create(UsuarioRol(usuario_id=usuario_id, rol_id=r) for r in rol_ids)


def _rol_de_dominio(rol: Rol) -> RolDominio:
    permisos = frozenset(p.permiso_id for p in rol.permisos.all())
    return RolDominio(rol.nombre, permisos, rol.es_sistema, rol.activo)


class AccesosOrm(RolesOrm):
    def bloquear_empresa(self, empresa_id):
        empresa = Empresa.objects.select_for_update().select_related("plan").get(pk=empresa_id)
        return empresa.plan.limite_usuarios

    def contar_activos_no_tecnicos(self, empresa_id) -> int:
        return Usuario.objects.filter(
            empresa_id=empresa_id, is_active=True, es_tecnico=False
        ).count()

    def existe_email(self, email) -> bool:
        return Usuario.objects.filter(email__iexact=email.strip()).exists()

    def crear_usuario(self, empresa_id, nombre, email, password) -> int:
        return Usuario.objects.create_user(
            email.strip(), password, nombre=nombre, empresa_id=empresa_id
        ).id

    def usuario(self, empresa_id, usuario_id):
        fila = Usuario.objects.filter(pk=usuario_id, empresa_id=empresa_id)
        datos = fila.values_list("is_active", "es_tecnico").first()
        if datos is None:
            raise NoEncontrado("No encontrado")
        return datos

    def actualizar_usuario(self, usuario_id, **campos) -> None:
        Usuario.objects.filter(pk=usuario_id).update(**campos)

    def administradores_activos(self, empresa_id) -> set[int]:
        return set(
            UsuarioRol.objects.filter(
                rol__empresa_id=empresa_id,
                rol__es_sistema=True,
                usuario__is_active=True,
            ).values_list("usuario_id", flat=True)
        )

    def _roles(self, empresa_id, rol_ids):
        filas = Rol.all_tenants.filter(empresa_id=empresa_id, pk__in=rol_ids)
        filas = list(filas.prefetch_related("permisos"))
        if len(filas) != len(set(rol_ids)):
            raise NoEncontrado("No encontrado")
        return filas

    def roles(self, empresa_id, rol_ids) -> list[RolDominio]:
        return [_rol_de_dominio(r) for r in self._roles(empresa_id, rol_ids)]

    def rol(self, empresa_id, rol_id) -> RolDominio:
        return self.roles(empresa_id, [rol_id])[0]

    def permisos_guardados(self, rol_id) -> set[str]:
        return set(RolPermiso.objects.filter(rol_id=rol_id).values_list("permiso_id", flat=True))

    def actualizar_rol(self, rol_id, nombre, permisos) -> None:
        Rol.all_tenants.filter(pk=rol_id).update(nombre=nombre)
        RolPermiso.objects.filter(rol_id=rol_id).delete()
        RolPermiso.objects.bulk_create(RolPermiso(rol_id=rol_id, permiso_id=p) for p in permisos)

    def cambiar_estado_rol(self, rol_id, activo) -> None:
        Rol.all_tenants.filter(pk=rol_id).update(activo=activo)

    def usuarios_con_rol(self, rol_id) -> int:
        return UsuarioRol.objects.filter(rol_id=rol_id).count()

    def eliminar_rol(self, rol_id) -> None:
        Rol.all_tenants.filter(pk=rol_id).delete()

    def nombres_roles(self, usuario_id) -> list[str]:
        filas = UsuarioRol.objects.filter(usuario_id=usuario_id)
        return sorted(filas.values_list("rol__nombre", flat=True))

    def revocar_tokens_de(self, usuario_id) -> None:
        ApiToken.all_tenants.filter(usuario_id=usuario_id, revocado_en__isnull=True).update(
            revocado_en=timezone.now()
        )

    def usuario_tecnico(self, empresa_id, nombre):
        fila = Usuario.objects.filter(empresa_id=empresa_id, es_tecnico=True, nombre=nombre)
        return fila.values_list("id", flat=True).first()

    def crear_usuario_tecnico(self, empresa_id, nombre) -> int:
        """No inicia sesión: contraseña inutilizable y `es_tecnico` (RF-TEN-45)."""
        email = f"{slugify(nombre)}.{empresa_id}.{secrets.token_hex(3)}@tecnico.illumi"
        return Usuario.objects.create_user(
            email, None, nombre=nombre, empresa_id=empresa_id, es_tecnico=True
        ).id

    def guardar_token(self, empresa_id, usuario_id, nombre, token_hash, prefijo, creado_por):
        return ApiToken.all_tenants.create(
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            nombre=nombre,
            token_hash=token_hash,
            prefijo=prefijo,
            creado_por_id=creado_por,
        ).id

    def token(self, empresa_id, token_id):
        fila = ApiToken.all_tenants.filter(empresa_id=empresa_id, pk=token_id)
        datos = fila.values_list("nombre", "revocado_en").first()
        if datos is None:
            raise NoEncontrado("No encontrado")
        return datos[0], datos[1] is not None

    def revocar_token(self, token_id) -> None:
        ApiToken.all_tenants.filter(pk=token_id).update(revocado_en=timezone.now())

    def auditar(self, empresa_id, actor_id, entidad, entidad_id, accion, antes, despues):
        AuditoriaAcceso.all_tenants.create(
            empresa_id=empresa_id,
            actor_id=actor_id,
            entidad=entidad,
            entidad_id=entidad_id,
            accion=accion,
            antes=antes,
            despues=despues,
        )


def roles_de_usuario(usuario_id: int) -> list[RolDominio]:
    filas = Rol.all_tenants.filter(usuarios__id=usuario_id).prefetch_related("permisos")
    return [_rol_de_dominio(r) for r in filas]
