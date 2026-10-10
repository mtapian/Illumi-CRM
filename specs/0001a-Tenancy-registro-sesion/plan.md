# Plan 0001a — Registro, sesión y suscripción

Estado: borrador

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/tenancy` (empresa, usuario, sesión, suscripción) y la base de `src/shared`. Es la primera spec que se implementa: incluye la base del proyecto (plan 000).

## 1. Archivos y responsabilidades

Todos los archivos son nuevos (no hay código todavía), salvo los marcados como **modifica**.

| Archivo | Responsabilidad | RF |
|---|---|---|
| `pyproject.toml`, `config/`, `.importlinter` | Proyecto Django, dependencias fijadas, contratos de capas y contextos | (plan 000) |
| `src/shared/domain/tenant.py` | `TenantContext` y manager base que falla sin tenant | (plan 000 §4) |
| `src/shared/infrastructure/secuencia.py` | `SequencePort.siguiente()` con `select_for_update` | (numeración de todas las specs) |
| `src/shared/domain/vigencia.py` | `valor_vigente()` para parámetros con fecha de vigencia (IGV, umbrales, plazos) | RF-TEN-16 |
| `src/shared/infrastructure/correo.py` | Outbox de correos: `encolar_correo()` en la transacción y envío fuera de ella | RF-TEN-09 |
| `src/tenancy/domain/ruc.py` | Value object `Ruc` (11 dígitos, prefijo, módulo 11) | RF-TEN-03 |
| `src/tenancy/domain/suscripcion.py` | Funciones puras del estado de la suscripción con `hoy` | RF-TEN-05, 18, 19, 20 |
| `src/tenancy/domain/sesion.py` | `bloqueo_por_intentos()` | RF-TEN-08 |
| `src/tenancy/domain/errores.py` | `RucInvalido`, `RucDuplicado`, `EmailDuplicado`, `IgvInvalido`… | todos los `SI … ENTONCES` |
| `src/tenancy/application/sembradores.py` | Puerto `SembradorInicial` y registro `registrar_sembrador()`; cada contexto registra el suyo | RF-TEN-01, 02 |
| `src/tenancy/application/registro.py` | `RegistrarEmpresa`: empresa + administrador + sembradores en una transacción | RF-TEN-01 a 05 |
| `src/tenancy/application/empresa.py` | `ActualizarEmpresa`, `CambiarIgv` | RF-TEN-15 a 17 |
| `src/tenancy/application/fachada.py` | `TenancyService` público: `igv_vigente()`, `parametro_vigente()`, `empresa_activa()`, `registrar_sembrador()` | RF-TEN-01, 16, 18 |
| `src/tenancy/infrastructure/models.py`, `repositorios.py` | Modelos de §2 y repositorios filtrados por tenant | §2 |
| `src/tenancy/interfaces/middleware.py` | `TenantMiddleware` (fija el tenant), `SuscripcionMiddleware` | RF-TEN-18, 21 |
| `src/tenancy/interfaces/auth.py` | Login con control de intentos y recuperación de contraseña | RF-TEN-06 a 09 |
| `src/tenancy/interfaces/views/*.py` + `templates/tenancy/*.html` | Pantallas de §5 | RF-TEN-01 a 09, 15 a 19 |
| `src/tenancy/interfaces/management/commands/vencer_suscripciones.py` | Cron diario: marca empresas vencidas | RF-TEN-18, 20 |
| `config/settings.py` (**modifica**) | `AUTH_USER_MODEL`, orden de middleware, HTTPS, expiración de sesión, hasher | RNF-TEN-01, 03, 04 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `tenancy_plan` | id, nombre, slug, precio_mensual, limite_usuarios null, limite_productos null, es_plan_prueba, dias_prueba, activo | UNIQUE(slug); un solo plan de prueba activo. Sus funcionalidades se agregan en 0001b | RF-TEN-05 |
| `tenancy_empresa` | id, ruc `CHAR(11)`, razon_social, nombre_comercial, direccion_fiscal, ubigeo, telefono, email, logo_ref, prefijo_lote, estado (`TRIAL`/`ACTIVA`/`VENCIDA`/`SUSPENDIDA`), plan_id, fecha_termino `DATE`, created_at | UNIQUE(ruc); `ruc` no editable | RF-TEN-01, 03, 15, 17, 18 |
| `tenancy_usuario` | `AUTH_USER_MODEL`: empresa_id null (null = super admin), email, nombre, password (hash), is_active, is_super, es_tecnico, intentos_fallidos, bloqueado_hasta | UNIQUE(email); un usuario técnico no puede iniciar sesión | RF-TEN-04, 06 a 08 |
| `tenancy_parametro_vigencia` | ambito (`PLATAFORMA` o empresa_id), clave (`igv_pct`, `umbral_boleta_identificada`, `plazo_envio_dias`, `retencion_anios`, `dias_prueba`), valor `NUMERIC`, vigente_desde `DATE` | UNIQUE(ambito, clave, vigente_desde); solo inserción | RF-TEN-05, 16 |
| `shared_secuencia` | empresa_id, documento, serie, ultimo_numero | UNIQUE(empresa_id, documento, serie) | (numeración de todas las specs) |
| `shared_correo` | empresa_id, destinatario, asunto, cuerpo, adjuntos_ref, estado, intentos, enviado_en | Outbox de correos | RF-TEN-09 |

## 3. Funciones puras (dominio, sin base de datos)

Toda función que depende de la fecha recibe `hoy: date` (hora de Lima) como parámetro; nunca la lee del reloj.

| Función | Qué hace | RF |
|---|---|---|
| `Ruc.validar(texto) -> Ruc` | 11 dígitos, prefijo 10/15/17/20, dígito verificador módulo 11 | RF-TEN-03 |
| `estado_suscripcion(estado, fecha_termino, hoy) -> Estado` | `VENCIDA` si `hoy > fecha_termino` (la fecha de término es inclusiva); respeta `SUSPENDIDA` | RF-TEN-18, 20 |
| `dias_para_vencer(fecha_termino, hoy) -> int \| None` | Días restantes; `None` si no hay fecha | RF-TEN-19 |
| `mostrar_aviso_vencimiento(fecha_termino, hoy) -> bool` | `0 ≤ dias_para_vencer ≤ 7` | RF-TEN-19 |
| `fecha_termino_prueba(fecha_registro, dias_prueba) -> date` | Fin de la prueba | RF-TEN-05 |
| `bloqueo_por_intentos(intentos, ultimo_fallo, ahora) -> datetime \| None` | 5 fallos ⇒ bloqueo de 15 minutos (valores de Q6) | RF-TEN-08 |
| `valor_vigente(historial, fecha) -> Decimal` | Valor con mayor `vigente_desde ≤ fecha` | RF-TEN-16 |
| `validar_igv(pct)` | 0 ≤ pct ≤ 100 con 2 decimales | RF-TEN-16 |

## 4. Algoritmos clave (pseudocódigo)

**Registro atómico de la empresa con sembradores** (RF-TEN-01 a 05):
```
# Al arrancar, cada contexto registra su sembrador (AppConfig.ready):
#   inventory → almacén "Principal" · catalog → unidades · finance → categorías de gasto
#   billing → series · sales → cliente genérico · tenancy (0001c) → roles iniciales + rol del admin

RegistrarEmpresa(datos):
  ruc = Ruc.validar(datos.ruc)                         # RF-TEN-03
  si existe empresa con ruc → RucDuplicado              # RF-TEN-03
  si existe usuario con email → EmailDuplicado          # RF-TEN-04
  en una transacción:                                   # RF-TEN-02
    plan = plan_de_prueba()
    empresa = crear(ruc, …, estado=TRIAL, plan, fecha_termino=fecha_termino_prueba(hoy, plan.dias_prueba))
    admin = crear_usuario(datos)
    con tenant_context(empresa):
      para cada s en sembradores_registrados():         # si uno falla, se revierte todo
        s.sembrar(empresa, admin, hoy)
  iniciar_sesion(admin)                                 # RF-TEN-05
```

**Control de suscripción en cada request** (RF-TEN-18, 21):
```
SuscripcionMiddleware(request):
  e = request.user.empresa
  si e y estado_suscripcion(e.estado, e.fecha_termino, hoy) ∈ {VENCIDA, SUSPENDIDA}
     y ruta ∉ {suscripcion, logout} → redirigir a /suscripcion
```

## 5. Interfaz

Django Templates + HTMX, responsive (usable en tablet).

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/registro` | Formulario de registro; errores de RUC y email junto al campo | RF-TEN-01 a 05 |
| `/login`, `/password-reset/*` | Login con mensaje por motivo (inactivo, suspendida, bloqueado); recuperación por email | RF-TEN-06 a 09 |
| `/dashboard` | Guía de primeros pasos en la empresa nueva; aviso de vencimiento cuando faltan ≤ 7 días | RF-TEN-05, 19 |
| `/suscripcion` | Plan, fecha de término, uso vs. límites (solo lectura) | RF-TEN-18 |
| `/configuracion/empresa` | Datos de la empresa; RUC de solo lectura; IGV con fecha de vigencia | RF-TEN-15 a 17 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Datos iniciales por **sembradores registrados**: cada contexto registra el suyo en `TenancyService` | `RegistrarEmpresa` llama directamente a los servicios de 002, 003, 006, 007 y 008 | Tenancy no depende de los demás contextos (grafo del plan 000) y 0001a se implementa antes que ellos; cada spec agrega su sembrador cuando existe |
| `estado_suscripcion` calculado con `hoy` en cada request + cron diario que persiste `VENCIDA` | Solo el cron | Si el cron falla, igual se bloquea el acceso a tiempo (RF-TEN-18) |
| IGV y parámetros tributarios en una tabla de vigencias | Columna `igv_pct` en la empresa | Constitución art. 5.1: reglas tributarias con vigencia |
| Correos por outbox (`shared_correo`) | Envío directo en la vista | Constitución art. 7.4: efectos externos fuera de la transacción |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/shared tests/tenancy tests/acceptance -k "E01a"`. Los `.feature` de `./features/` se ejecutan con pytest-bdd.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/tenancy/unit/test_ruc.py` | RUC válidos e inválidos (tabla de ejemplos) | RF-TEN-03 |
| Unitario | `tests/tenancy/unit/test_suscripcion.py` | Vencimiento inclusivo, aviso a 7 días, con `hoy` fijo en el límite | RF-TEN-05, 18, 19, 20 |
| Unitario | `tests/tenancy/unit/test_sesion.py` | Bloqueo al 5.º intento, no al 4.º | RF-TEN-08 |
| Unitario | `tests/shared/unit/test_vigencia.py` | `valor_vigente` antes, en y después de un cambio | RF-TEN-16 |
| Caso de uso | `tests/tenancy/usecases/test_registro.py` | Registro con sembradores falsos; uno que falla ⇒ nada creado; RUC y email duplicados | RF-TEN-01 a 05 |
| Integración | `tests/tenancy/integration/test_login.py` | Inactivo, suspendida, bloqueo por intentos, enlace de recuperación | RF-TEN-06 a 09 |
| Integración | `tests/tenancy/integration/test_suscripcion_mw.py` | Suscripción vencida, sesión abierta suspendida, cron sin borrar filas | RF-TEN-18, 20, 21 |
| Integración | `tests/tenancy/integration/test_empresa.py` | RUC no editable, IGV con vigencia | RF-TEN-15 a 17 |
| Aceptación | `features/*.feature` (3 archivos) | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-TEN-01, RF-TEN-02, RF-TEN-03, RF-TEN-04, RF-TEN-05 | §1 `registro.py`, `sembradores.py`, `ruc.py`, `suscripcion.py` · §3 `Ruc.validar`, `fecha_termino_prueba` · §4 registro · §5 `/registro` · §6 sembradores · §7 |
| RF-TEN-06, RF-TEN-07, RF-TEN-08, RF-TEN-09 | §1 `auth.py`, `sesion.py`, `correo.py` · §3 `bloqueo_por_intentos` · §5 `/login` · §7 `test_login.py` |
| RF-TEN-15, RF-TEN-16, RF-TEN-17 | §1 `empresa.py`, `vigencia.py` · §2 `tenancy_parametro_vigencia` · §3 `valor_vigente`, `validar_igv` · §5 `/configuracion/empresa` · §7 |
| RF-TEN-18, RF-TEN-19, RF-TEN-20, RF-TEN-21 | §1 `suscripcion.py`, `middleware.py`, `vencer_suscripciones` · §3 `estado_suscripcion`, `mostrar_aviso_vencimiento` · §4 control de suscripción · §5 `/suscripcion`, `/dashboard` · §7 |

## 9. Dependencias de dudas abiertas

- **Q6:** valores de `bloqueo_por_intentos` y de la expiración de sesión (`SESSION_COOKIE_AGE`); quedan como configuración.
- **Specs 0001c, 0002a, 0003a, 0006a, 0007a y 0008a:** cada una agrega su sembrador; hasta entonces, "Registro exitoso" se verifica solo en lo que ya existe.
