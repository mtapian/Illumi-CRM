"""Registrar empresa con prueba gratis (UC-TEN-01; RF-TEN-01 a 05)."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date

from shared.domain.documentos import Ruc
from tenancy.application.puertos import RegistroRepo
from tenancy.application.sembradores import RegistroSembradores
from tenancy.domain.errores import EmailDuplicado, RucDuplicado, SinPlanDePrueba
from tenancy.domain.suscripcion import fecha_termino_prueba


@dataclass(frozen=True)
class DatosRegistro:
    ruc: str
    razon_social: str
    nombre_comercial: str
    nombre: str
    email: str
    password: str


@dataclass(frozen=True)
class ResultadoRegistro:
    empresa_id: int
    admin_id: int


class RegistrarEmpresa:
    def __init__(
        self,
        repo: RegistroRepo,
        sembradores: RegistroSembradores,
        transaccion: Callable[[], AbstractContextManager],
    ):
        self._repo = repo
        self._sembradores = sembradores
        self._transaccion = transaccion

    def ejecutar(self, datos: DatosRegistro, hoy: date) -> ResultadoRegistro:
        ruc = Ruc.validar(datos.ruc)
        email = datos.email.strip().lower()
        if self._repo.existe_ruc(ruc.valor):
            raise RucDuplicado("Ya existe una empresa con este RUC")
        if self._repo.existe_email(email):
            raise EmailDuplicado("Este email ya está registrado")
        plan = self._repo.plan_de_prueba()
        if plan is None:
            raise SinPlanDePrueba("La plataforma no tiene un plan de prueba configurado")
        plan_id, dias_prueba = plan

        with self._transaccion():  # RF-TEN-02: todo o nada
            empresa_id = self._repo.crear_empresa(
                ruc.valor,
                datos.razon_social.strip(),
                datos.nombre_comercial.strip(),
                plan_id,
                fecha_termino_prueba(hoy, dias_prueba),
            )
            admin_id = self._repo.crear_usuario(
                empresa_id, datos.nombre.strip(), email, datos.password
            )
            self._sembradores.sembrar(empresa_id, admin_id, hoy)
        return ResultadoRegistro(empresa_id, admin_id)
