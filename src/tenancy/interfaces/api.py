"""API de integración (spec 0001d; RF-TEN-46 a 48, 54).

Cada consulta (stock, pedidos, ventas, productos, resultados) se implementa en su spec
heredando de `VistaApi` y declarando su `permiso`. Solo devuelve datos de la empresa del
token y según los permisos de su usuario técnico.
"""

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.views import APIView

from shared.domain.errores import AccesoDenegado
from shared.domain.tenant import tenant_context
from tenancy.domain.tokens import NO_AUTENTICADO, hash_token, rechazo_token
from tenancy.infrastructure.contenedor import actor_de, tenancy_service
from tenancy.infrastructure.models import ApiToken

SIN_API = "Tu plan no incluye la API de integración"


class TokenActorAuthentication(BaseAuthentication):
    """`Authorization: Token <token>`. Devuelve (usuario técnico, Actor)."""

    def authenticate(self, request):
        tipo, _, token = request.headers.get("Authorization", "").partition(" ")
        if tipo.lower() not in ("token", "bearer") or not token:
            raise AuthenticationFailed("Falta el token de API")
        fila = (
            ApiToken.all_tenants.select_related("usuario__empresa")
            .filter(token_hash=hash_token(token.strip()))
            .first()
        )
        if fila is None:
            raise AuthenticationFailed("Token inválido")
        usuario, hoy = fila.usuario, timezone.localdate()
        empresa = usuario.empresa
        motivo = rechazo_token(
            fila.revocado_en is not None,
            usuario.is_active,
            empresa.estado,
            empresa.fecha_termino,
            tenancy_service().habilitaciones_de(empresa.id, hoy),
            hoy,
        )
        if motivo == NO_AUTENTICADO:
            raise AuthenticationFailed("Token revocado o empresa sin acceso")
        if motivo:
            raise PermissionDenied(SIN_API)
        ApiToken.all_tenants.filter(pk=fila.pk).update(ultimo_uso_en=timezone.now())
        return usuario, actor_de(usuario, hoy)

    def authenticate_header(self, request):
        return "Token"  # así un token rechazado responde 401 y no 403


class VistaApi(APIView):
    """Base de las consultas de la API: autentica, exige `permiso` y fija la empresa."""

    authentication_classes = [TokenActorAuthentication]
    permiso: str

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        request.auth.exige(self.permiso)
        self._empresa = tenant_context(request.auth.empresa_id)
        self._empresa.__enter__()

    def finalize_response(self, request, response, *args, **kwargs):
        if empresa := getattr(self, "_empresa", None):
            empresa.__exit__(None, None, None)
            self._empresa = None
        return super().finalize_response(request, response, *args, **kwargs)

    def handle_exception(self, exc):
        if isinstance(exc, AccesoDenegado):
            exc = PermissionDenied(exc.mensaje)
        return super().handle_exception(exc)
