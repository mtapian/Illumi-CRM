# Plan 001 — Tenancy y accesos

Estado: borrador

Spec: `./spec.md` · Base técnica: `../000-arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contextos: `src/tenancy` (empresas, planes, usuarios, roles, tokens) y `src/shared/domain/accesos.py` (catálogo de permisos como código, usado por todos los contextos).

## 1. Archivos y responsabilidades

Todos los archivos son nuevos (no hay código todavía), salvo los marcados como **modifica**.

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/shared/domain/accesos.py` | Catálogo de módulos, funcionalidades, permisos y dependencias como constantes (`CATALOGO`, clase `P` con los códigos) | RF-TEN-26, 31, 35, 49 |
| `src/shared/domain/vigencia.py` | `valor_vigente()` para parámetros con fecha de vigencia (IGV, umbrales, plazos) | RF-TEN-16 |
| `src/shared/application/autorizacion.py` | `Actor` (permisos efectivos) y clase base `CasoDeUso` con `permiso_requerido` | RF-TEN-49, 51 |
| `src/shared/infrastructure/correo.py` | Outbox de correos: `encolar_correo()` en la transacción y envío fuera de ella | RF-TEN-09 |
| `src/tenancy/domain/ruc.py` | Value object `Ruc` (11 dígitos, prefijo, módulo 11) | RF-TEN-03 |
| `src/tenancy/domain/habilitaciones.py` | Funciones puras de habilitaciones, dependencias y vigencia de ajustes | RF-TEN-26, 28, 30, 31, 33, 34 |
| `src/tenancy/domain/permisos.py` | Funciones puras de permisos efectivos y control de escalada | RF-TEN-10, 14, 36, 37, 39, 41, 53 |
| `src/tenancy/domain/suscripcion.py` | Funciones puras del estado de la suscripción con `hoy` | RF-TEN-05, 18, 19, 20 |
| `src/tenancy/domain/plantillas.py` | Plantillas de rol iniciales como datos (tabla de la spec) | RF-TEN-01 |
| `src/tenancy/domain/errores.py` | Errores de dominio con código (`RucInvalido`, `LimiteUsuariosPlan`, `UltimoAdministrador`, `EscaladaDePrivilegios`…) | todos los `SI … ENTONCES` |
| `src/tenancy/application/registro.py` | `RegistrarEmpresa` (operación atómica que siembra datos de las demás specs vía sus fachadas) | RF-TEN-01 a 05 |
| `src/tenancy/application/usuarios.py` | `CrearUsuario`, `EditarUsuario`, `AsignarRoles`, `CambiarEstadoUsuario`, `PermisosEfectivosQuery` | RF-TEN-10 a 14, 53 |
| `src/tenancy/application/empresa.py` | `ActualizarEmpresa`, `CambiarIgv` | RF-TEN-15 a 17 |
| `src/tenancy/application/plataforma.py` | `ActivarPlan`, `SuspenderEmpresa`, `ReactivarEmpresa`, `CambiarPlan`, `ConfigurarFuncionalidadesPlan`, `AgregarFuncionalidad`, `QuitarFuncionalidad`, `RevocarAjuste`, `ImpactoQuitarQuery` | RF-TEN-22 a 34 |
| `src/tenancy/application/roles.py` | `CrearRol`, `EditarRol`, `DuplicarRol`, `DesactivarRol`, `EliminarRol` | RF-TEN-35 a 39 |
| `src/tenancy/application/auditoria.py` | `registrar_auditoria()` y `AuditoriaAccesosQuery` | RF-TEN-43, 44 |
| `src/tenancy/application/tokens.py` | `CrearTokenApi`, `RevocarTokenApi`, `TokensApiQuery`, desactivación del usuario técnico | RF-TEN-45 a 48, 54 |
| `src/tenancy/application/fachada.py` | `TenancyService` público: `actor_de()`, `igv_vigente()`, `parametro_vigente()`, `empresa_activa()` | RF-TEN-16, 18 |
| `src/tenancy/infrastructure/models.py` | Modelos ORM de §2 | §2 |
| `src/tenancy/infrastructure/repositorios.py` | Repositorios filtrados por tenant | RF-TEN-52 |
| `src/tenancy/infrastructure/sql/auditoria_inmutable.sql` | Trigger que impide `UPDATE`/`DELETE` en la auditoría | RF-TEN-43 |
| `src/tenancy/infrastructure/migrations/0002_catalogo.py` | Data migration que sincroniza `CATALOGO` con sus tablas | RF-TEN-35 |
| `src/tenancy/interfaces/middleware.py` | `TenantMiddleware`, `SuscripcionMiddleware`, `AccesoMiddleware` (construye el `Actor` en cada request) | RF-TEN-18, 21, 40, 42, 52 |
| `src/tenancy/interfaces/auth.py` | Login con control de intentos, recuperación de contraseña; `TokenActorAuthentication` para DRF | RF-TEN-06 a 09, 46 a 48 |
| `src/tenancy/interfaces/views/*.py` + `templates/tenancy/*.html` | Pantallas de §5 | RF-TEN-01 a 48 |
| `src/tenancy/interfaces/templatetags/acceso.py` | `{% puede "permiso" %}` para menú y botones | RF-TEN-50 |
| `src/tenancy/interfaces/management/commands/vencer_suscripciones.py` | Cron diario: marca empresas vencidas | RF-TEN-18 |
| `config/settings.py` (**modifica**) | `AUTH_USER_MODEL`, orden de middleware, HTTPS, expiración de sesión | RNF-TEN-03, 04 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `tenancy_plan` | id, nombre, slug, precio_mensual, limite_usuarios null, limite_productos null, es_plan_prueba, dias_prueba, activo | UNIQUE(slug); un solo plan de prueba activo | RF-TEN-05, 11, 25 |
| `tenancy_modulo`, `tenancy_funcionalidad`, `tenancy_permiso`, `tenancy_funcionalidad_dependencia` | códigos, nombres, módulo, dependencias, `obsoleto` | Sincronizados desde `CATALOGO`; nunca se borran códigos con referencias | RF-TEN-26, 31, 35 |
| `tenancy_plan_funcionalidad` | plan_id, funcionalidad_codigo | PK compuesta | RF-TEN-25, 27 |
| `tenancy_empresa` | id, ruc `CHAR(11)`, razon_social, nombre_comercial, direccion_fiscal, ubigeo, telefono, email, logo_ref, prefijo_lote, estado (`TRIAL`/`ACTIVA`/`VENCIDA`/`SUSPENDIDA`), plan_id, fecha_termino `DATE`, created_at | UNIQUE(ruc); `ruc` no editable | RF-TEN-01, 03, 15, 17, 18, 22 |
| `tenancy_empresa_ajuste` | empresa_id, funcionalidad_codigo, tipo (`AGREGAR`/`QUITAR`), vigente_hasta `DATE` null, motivo, creado_por, revocado_en | Un ajuste activo por funcionalidad | RF-TEN-29, 30 |
| `tenancy_usuario` | `AUTH_USER_MODEL`: empresa_id null (null = super admin), email, nombre, password (hash), is_active, is_super, es_tecnico, intentos_fallidos, bloqueado_hasta | UNIQUE(email); un usuario técnico no puede iniciar sesión | RF-TEN-04, 06 a 13 |
| `tenancy_rol`, `tenancy_rol_permiso`, `tenancy_usuario_rol` | rol de la empresa, sus permisos, sus usuarios | UNIQUE(empresa_id, nombre); un solo rol de sistema por empresa | RF-TEN-35 a 39 |
| `tenancy_auditoria_acceso` | empresa_id, actor_id, entidad (`ROL`, `USUARIO_ROL`, `USUARIO`, `AJUSTE`, `PLAN`, `TOKEN_API`), entidad_id, accion, antes, despues, created_at | Solo inserción (trigger) | RF-TEN-43, 44 |
| `tenancy_actividad` | empresa_id, actor_id, accion, motivo, created_at | Solo inserción | RF-TEN-22 |
| `tenancy_parametro_vigencia` | ambito (`PLATAFORMA` o empresa_id), clave (`igv_pct`, `umbral_boleta_identificada`, `plazo_envio_dias`, `retencion_anios`, `dias_prueba`), valor `NUMERIC`, vigente_desde `DATE` | UNIQUE(ambito, clave, vigente_desde); solo inserción | RF-TEN-05, 16 |
| `tenancy_api_token` | empresa_id, usuario_id (técnico), nombre, token_hash, prefijo, creado_por, creado_en, ultimo_uso_en, revocado_en | UNIQUE(token_hash); nunca se guarda en claro | RF-TEN-45 a 48, 54 |
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
| `ajuste_vigente(ajuste, hoy) -> bool` | `vigente_hasta is None or hoy <= vigente_hasta` | RF-TEN-30 |
| `habilitaciones_efectivas(funcs_plan, ajustes, hoy) -> frozenset` | `CORE ∪ (plan ∪ agregados vigentes) − quitados vigentes` | RF-TEN-28, 30, 33 |
| `estado_funcionalidad(f, funcs_plan, ajustes, hoy) -> str` | Incluida / Agregada / Quitada / No incluida | RF-TEN-28 |
| `dependencias_faltantes(conjunto) -> list` | Funcionalidades requeridas que no están en el conjunto | RF-TEN-26, 31 |
| `dependientes_afectados(f, conjunto) -> list` | Funcionalidades habilitadas que dejarían de cumplir sus dependencias si se quita `f` | RF-TEN-31 |
| `funcionalidades_de_modulo(modulo) -> list` | Para habilitar o deshabilitar un módulo completo | RF-TEN-34 |
| `permisos_efectivos(roles_activos, habilitadas) -> frozenset` | Rol de sistema ⇒ todos los habilitados; si no, `(∪ roles) ∩ permisos(habilitadas)` | RF-TEN-10, 37, 39, 41 |
| `origen_permisos(roles, habilitadas) -> dict` | Para la ficha: permiso → roles que lo dan, o "no disponible por el plan" | RF-TEN-14 |
| `validar_permisos_rol(permisos, habilitadas)` | Lanza `PermisoNoHabilitado` | RF-TEN-36 |
| `validar_escalada(permisos_actor, es_admin_actor, permisos_a_dar, da_rol_admin)` | Lanza `EscaladaDePrivilegios` | RF-TEN-53 |
| `quedan_administradores(usuarios_activos_admin_despues) -> bool` | Al menos un Administrador activo | RF-TEN-12 |
| `cabe_en_limite(activos_no_tecnicos, limite) -> bool` | `limite is None or activos < limite` | RF-TEN-11 |
| `bloqueo_por_intentos(intentos, ultimo_fallo, ahora) -> datetime \| None` | 5 fallos ⇒ bloqueo de 15 minutos (valores de Q6) | RF-TEN-08 |
| `valor_vigente(historial, fecha) -> Decimal` | Valor con mayor `vigente_desde ≤ fecha` | RF-TEN-16 |
| `validar_igv(pct)` | 0 ≤ pct ≤ 100 con 2 decimales | RF-TEN-16 |
| `prefijo_token(token) -> str` | Primeros 8 caracteres para mostrar | RF-TEN-45 |
| `token_utilizable(token, usuario_tecnico, empresa, habilitadas, hoy) -> bool` | No revocado, usuario activo, empresa activa, API habilitada | RF-TEN-46, 47, 54 |

## 4. Algoritmos clave (pseudocódigo)

**Registro atómico de la empresa** (RF-TEN-01 a 05):
```
RegistrarEmpresa(datos):
  ruc = Ruc.validar(datos.ruc)                         # RF-TEN-03
  si existe empresa con ruc → RucDuplicado              # RF-TEN-03
  si existe usuario con email → EmailDuplicado          # RF-TEN-04
  en una transacción:                                   # RF-TEN-02
    plan = plan_de_prueba()
    empresa = crear(ruc, …, estado=TRIAL, fecha_termino=fecha_termino_prueba(hoy, plan.dias_prueba))
    con tenant_context(empresa):
      InventarioService.crear_almacen("Principal")      # spec 003
      CatalogoService.sembrar_unidades()                # spec 002
      FinanzasService.sembrar_categorias_gasto()        # spec 008
      FacturacionService.sembrar_series()               # spec 007
      VentasService.crear_cliente_generico()            # spec 006
      roles = crear_rol_sistema() + plantillas filtradas por habilitaciones_efectivas(plan, [], hoy)
      admin = crear_usuario(datos, rol=Administrador)
  iniciar_sesion(admin)                                 # RF-TEN-05
```

**Construcción del `Actor` en cada request** (RF-TEN-18, 21, 40, 41, 42, 49):
```
AccesoMiddleware(request):
  u = request.user; e = u.empresa
  si estado_suscripcion(e.estado, e.fecha_termino, hoy) ∈ {VENCIDA, SUSPENDIDA}
     y ruta ∉ {suscripcion, logout} → redirigir a /suscripcion        # RF-TEN-18, 21
  habilitadas = habilitaciones_efectivas(plan(e), ajustes(e), hoy)     # se recalcula en cada request: RF-TEN-40, 42
  permisos = permisos_efectivos(roles_activos(u), habilitadas)
  request.actor = Actor(u, e, permisos)
  si permisos vacío → pantalla "No tienes módulos asignados"           # RF-TEN-41
```

**Quitar una funcionalidad a una empresa** (RF-TEN-29, 31, 32, 33):
```
QuitarFuncionalidad(empresa, f, motivo, vigente_hasta):
  exigir motivo
  afectados = dependientes_afectados(f, habilitaciones_efectivas(…, hoy))
  si afectados → DependientesHabilitados(afectados)
  si no confirmado: devolver ImpactoQuitarQuery(empresa, f)   # cuenta OP en proceso, comprobantes pendientes
  guardar ajuste QUITAR; registrar_auditoria(AJUSTE, antes, despues)
  # no se borra ningún dato ni rol (RF-TEN-33)
```

**Asignar roles sin escalada** (RF-TEN-10 a 12, 53):
```
AsignarRoles(actor, usuario, roles_nuevos):
  actor.exige(core.usuario.gestionar)
  validar_escalada(actor.permisos, actor.es_admin, ∪permisos(roles_nuevos), "Administrador" ∈ roles_nuevos)
  con lock de la empresa:                                     # dos admins en paralelo
     si not quedan_administradores(admins_activos_tras_el_cambio) → UltimoAdministrador
     guardar; registrar_auditoria(USUARIO_ROL, antes, despues)
```

**Autenticación por token** (RF-TEN-46 a 48, 54):
```
TokenActorAuthentication(request):
  t = buscar por hash(token del header)
  si no t o not token_utilizable(t, t.usuario, t.empresa, habilitadas, hoy) → 401
  fijar TenantContext(t.empresa); request.actor = Actor(t.usuario, …)
  t.ultimo_uso_en = ahora
```

## 5. Interfaz

Django Templates + HTMX, responsive (usable en tablet). El menú y los botones se pintan con `{% puede %}` (RF-TEN-50).

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/registro` | Formulario de registro; errores de RUC y email junto al campo | RF-TEN-01 a 05 |
| `/login`, `/password-reset/*` | Login con mensaje por motivo (inactivo, suspendida, bloqueado); recuperación por email | RF-TEN-06 a 09 |
| `/dashboard` | Guía de primeros pasos en la empresa nueva; aviso de vencimiento cuando faltan ≤ 7 días | RF-TEN-05, 19 |
| `/suscripcion` | Plan, fecha de término, uso vs. límites, módulos habilitados (solo lectura) | RF-TEN-18 |
| `/usuarios/` | Listado; formulario con selección múltiple de roles; ficha con permisos efectivos agrupados por módulo y su origen | RF-TEN-10 a 14, 53 |
| `/roles/` | Matriz módulo → funcionalidad → permisos (casillas; las no habilitadas en gris con "No incluido en tu plan"); acciones duplicar, desactivar, eliminar | RF-TEN-35 a 39 |
| `/configuracion/empresa` | Datos de la empresa; RUC de solo lectura; IGV con fecha de vigencia | RF-TEN-15 a 17 |
| `/auditoria/accesos` | Tabla filtrable de cambios (antes → después) | RF-TEN-43, 44 |
| `/integracion/tokens` | Listado (prefijo, creado, último uso); al crear, un panel muestra el token completo una sola vez con botón "Copiar" | RF-TEN-45 a 47, 54 |
| `/plataforma/empresas/` | Listado con filtros por estado y plan; activar, suspender, reactivar con motivo | RF-TEN-22 a 24 |
| `/plataforma/planes/<id>` | Checklist de funcionalidades por módulo, límites; al guardar, modal "Afecta a N empresas" | RF-TEN-25 a 27 |
| `/plataforma/empresas/<id>/modulos` | Estado por funcionalidad (insignias); agregar o quitar con motivo y fecha de fin; modal de impacto; atajo por módulo | RF-TEN-28 a 34 |
| Página "Acceso denegado" (403) y "No encontrado" (404) | Mensajes de la spec; un registro de otra empresa siempre da 404 | RF-TEN-42, 49, 52 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Catálogo de permisos como código en `shared` | Permisos de Django por modelo (`add_`, `change_`) | Los permisos son por caso de uso y por funcionalidad comercial, no CRUD por tabla (constitución art. 6.1) |
| Permisos efectivos recalculados en cada request (2 consultas) | Caché con versión por empresa | Simplicidad (art. 7.6) y aplicación inmediata de cambios (RF-TEN-40); se agrega caché solo si se mide lentitud |
| `estado_suscripcion` calculado con `hoy` en cada request + cron diario que persiste `VENCIDA` | Solo el cron | Si el cron falla, igual se bloquea el acceso a tiempo (RF-TEN-18) |
| IGV y parámetros tributarios en una tabla de vigencias | Columna `igv_pct` en la empresa | Constitución art. 5.1: reglas tributarias con vigencia |
| Token guardado como hash SHA-256 y mostrado una sola vez | Guardarlo cifrado para volver a mostrarlo | Constitución art. 6.2 (v1.1.0) |
| Un registro de otra empresa responde 404 | Responder 403 | No revela que el registro existe (caso límite de la spec, art. 3) |
| Correos por outbox (`shared_correo`) | Envío directo en la vista | Constitución art. 7.4: efectos externos fuera de la transacción |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/tenancy tests/acceptance -k "E01"`. Los `.feature` de `./features/` se ejecutan con pytest-bdd.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/tenancy/unit/test_ruc.py` | RUC válidos e inválidos (tabla de ejemplos) | RF-TEN-03 |
| Unitario | `tests/tenancy/unit/test_suscripcion.py` | Vencimiento inclusivo, aviso a 7 días, con `hoy` fijo en el límite | RF-TEN-05, 18, 19 |
| Unitario | `tests/tenancy/unit/test_habilitaciones.py` | Plan ± ajustes, vigencia el día exacto, dependencias, módulo completo | RF-TEN-26, 28, 30, 31, 34 |
| Unitario | `tests/tenancy/unit/test_permisos.py` | Unión de roles ∩ habilitadas, rol de sistema, rol inactivo, permisos conservados no efectivos, escalada | RF-TEN-10, 14, 36, 37, 39, 41, 53 |
| Unitario | `tests/shared/unit/test_vigencia.py` | `valor_vigente` antes, en y después de un cambio | RF-TEN-16 |
| Caso de uso | `tests/tenancy/usecases/test_registro.py` | Registro siembra todo; falla en un paso ⇒ nada creado | RF-TEN-01, 02, 04 |
| Caso de uso | `tests/tenancy/usecases/test_usuarios.py` | Límite sin técnicos, último administrador, no borrar | RF-TEN-11 a 13 |
| Caso de uso | `tests/tenancy/usecases/test_plataforma.py` | Activar, suspender, cambiar plan con ajustes, impacto | RF-TEN-22 a 27, 29, 32, 33 |
| Caso de uso | `tests/tenancy/usecases/test_tokens.py` | Token visible una vez, revocación, usuario técnico desactivado, empresa suspendida | RF-TEN-45 a 47, 54 |
| Integración | `tests/tenancy/integration/test_login.py` | Inactivo, suspendida, bloqueo por intentos, enlace de recuperación | RF-TEN-06 a 09 |
| Integración | `tests/tenancy/integration/test_middleware.py` | Suscripción vencida, cambios aplicados en la siguiente request, sesión abierta suspendida | RF-TEN-18, 21, 40, 42 |
| Integración | `tests/tenancy/integration/test_concurrencia.py` | Dos admins se desactivan a la vez (`TransactionTestCase`) | RF-TEN-12 |
| Integración | `tests/tenancy/integration/test_api_token.py` | Llamada con token: solo datos de su empresa, paginada, según permisos | RF-TEN-46, 48 |
| Integración | `tests/tenancy/integration/test_auditoria.py` | Auditoría de roles, usuarios, ajustes y tokens; trigger de inmutabilidad | RF-TEN-43, 44 |
| Integración | `tests/tenancy/integration/test_empresa.py` | RUC no editable, IGV con vigencia | RF-TEN-15 a 17 |
| Meta-test | `tests/meta/test_autorizacion.py` | Todo `CasoDeUso` declara un permiso del catálogo y falla sin él (cubre las specs 001–008) | RF-TEN-49, RNF-TEN-06 |
| Meta-test | `tests/meta/test_aislamiento.py` | Todos los modelos de empresa y rutas con `<id>`: datos de B invisibles desde A (404) | RF-TEN-52, RNF-TEN-05 |
| Integración | `tests/tenancy/integration/test_ui_permisos.py` | Menú y botones según permisos; costos ocultos sin `inventario.costo.ver` (pantalla, CSV, API) | RF-TEN-50, 51 |
| Aceptación | `features/*.feature` (5 archivos) | Escenarios de la spec | todos |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-TEN-01, RF-TEN-02, RF-TEN-03, RF-TEN-04, RF-TEN-05 | §1 `registro.py`, `ruc.py`, `suscripcion.py` · §3 `Ruc.validar`, `fecha_termino_prueba` · §4 registro atómico · §5 `/registro` · §7 |
| RF-TEN-06, RF-TEN-07, RF-TEN-08, RF-TEN-09 | §1 `auth.py`, `correo.py` · §3 `bloqueo_por_intentos` · §5 `/login` · §7 `test_login.py` |
| RF-TEN-10, RF-TEN-11, RF-TEN-12, RF-TEN-13, RF-TEN-14, RF-TEN-53 | §1 `usuarios.py`, `permisos.py` · §3 `cabe_en_limite`, `quedan_administradores`, `origen_permisos`, `validar_escalada` · §4 asignar roles · §5 `/usuarios/` · §7 |
| RF-TEN-15, RF-TEN-16, RF-TEN-17 | §1 `empresa.py`, `vigencia.py` · §2 `tenancy_parametro_vigencia` · §3 `valor_vigente`, `validar_igv` · §5 `/configuracion/empresa` · §7 |
| RF-TEN-18, RF-TEN-19, RF-TEN-20, RF-TEN-21 | §1 `suscripcion.py`, `middleware.py`, `vencer_suscripciones` · §3 `estado_suscripcion`, `mostrar_aviso_vencimiento` · §4 construcción del Actor · §5 `/suscripcion`, `/dashboard` · §7 |
| RF-TEN-22, RF-TEN-23, RF-TEN-24 | §1 `plataforma.py` · §2 `tenancy_actividad` · §5 `/plataforma/empresas/` · §7 `test_plataforma.py` |
| RF-TEN-25, RF-TEN-26, RF-TEN-27 | §1 `plataforma.py`, `habilitaciones.py` · §3 `dependencias_faltantes` · §5 `/plataforma/planes/<id>` · §7 |
| RF-TEN-28, RF-TEN-29, RF-TEN-30, RF-TEN-31, RF-TEN-32, RF-TEN-33, RF-TEN-34 | §1 `plataforma.py`, `habilitaciones.py` · §3 `ajuste_vigente`, `habilitaciones_efectivas`, `estado_funcionalidad`, `dependientes_afectados`, `funcionalidades_de_modulo` · §4 quitar funcionalidad · §5 `/plataforma/empresas/<id>/modulos` · §7 |
| RF-TEN-35, RF-TEN-36, RF-TEN-37, RF-TEN-38, RF-TEN-39 | §1 `roles.py`, `permisos.py` · §3 `validar_permisos_rol`, `permisos_efectivos` · §5 `/roles/` · §7 `test_permisos.py` |
| RF-TEN-40, RF-TEN-41, RF-TEN-42 | §1 `middleware.py` · §4 construcción del Actor · §5 403/"sin módulos" · §7 `test_middleware.py` |
| RF-TEN-43, RF-TEN-44 | §1 `auditoria.py`, `auditoria_inmutable.sql` · §5 `/auditoria/accesos` · §7 `test_auditoria.py` |
| RF-TEN-45, RF-TEN-46, RF-TEN-47, RF-TEN-48, RF-TEN-54 | §1 `tokens.py`, `auth.py` · §3 `prefijo_token`, `token_utilizable` · §4 autenticación por token · §5 `/integracion/tokens` · §7 |
| RF-TEN-49, RF-TEN-50, RF-TEN-51, RF-TEN-52 | §1 `autorizacion.py`, `acceso.py`, `repositorios.py` · §5 menú y 404 · §7 meta-tests y `test_ui_permisos.py` |

## 9. Dependencias de dudas abiertas

- **Q6:** valores de `bloqueo_por_intentos` y de la expiración de sesión (`SESSION_COOKIE_AGE`); quedan como configuración.
- **Q8:** contenido de cada plan; es dato (`tenancy_plan`, `tenancy_plan_funcionalidad`), no cambia el código.
