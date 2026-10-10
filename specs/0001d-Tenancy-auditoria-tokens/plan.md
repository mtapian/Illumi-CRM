# Plan 0001d — Auditoría de accesos y tokens de API

Estado: borrador

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contexto: `src/tenancy` (auditoría y tokens). Requiere 0001a, 0001b y 0001c.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/tenancy/domain/tokens.py` | `prefijo_token()`, `token_utilizable()` | RF-TEN-45 a 47, 54 |
| `src/tenancy/application/auditoria.py` | `registrar_auditoria()` y `AuditoriaAccesosQuery` | RF-TEN-43, 44 |
| `src/tenancy/application/usuarios.py`, `roles.py` (**modifica**) | Llaman a `registrar_auditoria()` en cada cambio de rol, permisos, asignación o estado | RF-TEN-43 |
| `src/tenancy/application/tokens.py` | `CrearTokenApi`, `RevocarTokenApi`, `TokensApiQuery`; invalidación al desactivar el usuario técnico | RF-TEN-45 a 47, 54 |
| `src/tenancy/infrastructure/models.py` (**modifica**) | Modelos de §2 | §2 |
| `src/tenancy/infrastructure/sql/auditoria_inmutable.sql` | Trigger que impide `UPDATE`/`DELETE` en la auditoría | RF-TEN-43 |
| `src/tenancy/interfaces/auth.py` (**modifica**) | `TokenActorAuthentication` para DRF | RF-TEN-46 a 48, 54 |
| `src/tenancy/interfaces/views/*.py` + `templates/tenancy/*.html` | Pantallas de §5 | RF-TEN-44, 45, 47 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `tenancy_auditoria_acceso` | empresa_id, actor_id, entidad (`ROL`, `USUARIO_ROL`, `USUARIO`, `TOKEN_API`), entidad_id, accion, antes, despues, created_at | Solo inserción (trigger) | RF-TEN-43, 44 |
| `tenancy_api_token` | empresa_id, usuario_id (técnico), nombre, token_hash, prefijo, creado_por, creado_en, ultimo_uso_en, revocado_en | UNIQUE(token_hash); nunca se guarda en claro | RF-TEN-45 a 48, 54 |

El historial de habilitaciones que ve el super admin (RF-TEN-44) se lee de `tenancy_empresa_ajuste` y `tenancy_actividad` (spec 0001b); no se duplica.

## 3. Funciones puras (dominio, sin base de datos)

| Función | Qué hace | RF |
|---|---|---|
| `prefijo_token(token) -> str` | Primeros 8 caracteres para mostrar | RF-TEN-45 |
| `token_utilizable(token, usuario_tecnico, empresa, habilitadas, hoy) -> bool` | No revocado, usuario activo, empresa activa (`estado_suscripcion` de 0001a), API habilitada | RF-TEN-46, 47, 54 |

## 4. Algoritmos clave (pseudocódigo)

**Crear token** (RF-TEN-43, 45, 46):
```
CrearTokenApi(actor, nombre, roles_tecnico):
  actor.exige(api.token.gestionar)
  si "API de integración" ∉ habilitadas o empresa no activa → rechazar   # RF-TEN-46
  tecnico = usuario técnico existente o crear(es_tecnico=True, roles_tecnico)
  token = secrets.token_urlsafe(32)
  guardar(token_hash=sha256(token), prefijo=prefijo_token(token))
  registrar_auditoria(TOKEN_API, antes=None, despues={nombre, prefijo})
  devolver token          # única vez que sale en claro
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

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/auditoria/accesos` | Tabla filtrable de cambios (antes → después); el super admin ve además el historial de habilitaciones | RF-TEN-43, 44 |
| `/integracion/tokens` | Listado (prefijo, creado, último uso); al crear, un panel muestra el token completo una sola vez con botón "Copiar" | RF-TEN-45 a 47, 54 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Token guardado como hash SHA-256 y mostrado una sola vez | Guardarlo cifrado para volver a mostrarlo | Constitución art. 6.2 (v1.1.0) |
| Auditoría inmutable por trigger | Solo por convención en el código | Constitución art. 7.3: la base de datos es la red de seguridad |
| La auditoría se agrega a los casos de uso de 0001c en esta spec | Auditar desde 0001c | El orden de las specs: la tabla y el trigger nacen aquí; 0001c no queda bloqueada |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/tenancy tests/acceptance -k "E01d"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/tenancy/unit/test_tokens.py` | `token_utilizable`: revocado, técnico inactivo, empresa suspendida o vencida, API no habilitada | RF-TEN-46, 47, 54 |
| Caso de uso | `tests/tenancy/usecases/test_tokens.py` | Token visible una vez, solo hash en la BD, revocación, usuario técnico desactivado | RF-TEN-45, 47, 54 |
| Integración | `tests/tenancy/integration/test_api_token.py` | Llamada con token: solo datos de su empresa, paginada, según permisos; 401/403 | RF-TEN-46, 48 |
| Integración | `tests/tenancy/integration/test_auditoria.py` | Auditoría de roles, usuarios y tokens; trigger de inmutabilidad; filtros | RF-TEN-43, 44 |
| Aceptación | `features/auditoria_accesos.feature`, `features/tokens_api.feature` | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-TEN-43, RF-TEN-44 | §1 `auditoria.py`, `auditoria_inmutable.sql` · §2 `tenancy_auditoria_acceso` · §5 `/auditoria/accesos` · §7 `test_auditoria.py` |
| RF-TEN-45, RF-TEN-46, RF-TEN-47, RF-TEN-48, RF-TEN-54 | §1 `tokens.py`, `auth.py` · §2 `tenancy_api_token` · §3 `prefijo_token`, `token_utilizable` · §4 crear token, autenticación · §5 `/integracion/tokens` · §7 |

## 9. Dependencias de dudas abiertas

- **épica 0002, 003, 006 y 008:** implementan las consultas de la API (RF-TEN-48); aquí se prueba la autenticación con un endpoint de prueba.
