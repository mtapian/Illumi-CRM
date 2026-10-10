# Plan 000 — Arquitectura transversal

| Campo | Valor |
|---|---|
| Estado | borrador |
| Aplica a | Todas las épicas (E01–E08) |
| PRD | `../../PRD.md` |

---

## 1. Decisiones de arquitectura (ADR resumidos)

| ID | Decisión | Alternativas descartadas | Motivo |
|---|---|---|---|
| ADR-01 | Python 3.12 + Django 5.2 LTS | Mantener Laravel | Decisión del PO; stack habitual del equipo |
| ADR-02 | Monolito modular con **arquitectura hexagonal pragmática** | Microservicios; Django "clásico" (lógica en modelos/vistas) | Reglas de costo y stock testeables sin BD; un solo despliegue |
| ADR-03 | PostgreSQL 16 | MySQL (referencia) | `NUMERIC` exacto, `CHECK`, `SELECT … FOR UPDATE`, RLS futuro |
| ADR-04 | Multi-tenant con BD compartida y columna `empresa_id` | Schema por tenant (`django-tenants`), BD por tenant | Operación simple; probado en la referencia |
| ADR-05 | Django Templates + HTMX | SPA (React/Vue) | Mínimo para operar; sin build de frontend |
| ADR-06 | DRF solo para la API de integración | API-first total | La UI no consume la API en el MVP |
| ADR-07 | Tareas diferidas con management commands + cron | Celery + Redis | Volumen bajo; se migra si hace falta |
| ADR-08 | Facturación vía puerto `EmisorComprobantes` + adaptador PSE | Firma UBL directa en Python | Python no tiene un equivalente maduro a Greenter; menos riesgo |
| ADR-09 | Tests de aceptación con `pytest-bdd` sobre los `.feature` | `behave` | Integra con pytest y sus fixtures |
| ADR-10 | **PL/pgSQL como red de seguridad**: las reglas viven en el dominio Python y la BD las refuerza con constraints, triggers, funciones atómicas y vistas de reporte (ver §5.1) | Lógica transaccional en stored procedures; ORM sin objetos de BD | Las reglas se prueban sin BD y la BD impide corrupción aunque haya un bug o un acceso directo |
| ADR-11 | **Autorización por permisos con catálogo como código** (módulo → funcionalidad → permiso), habilitaciones por plan/empresa y roles por tenant; el caso de uso verifica el permiso con un `Actor` | Roles fijos con `if rol in (...)`; `django.contrib.auth` permissions/groups por modelo | Los permisos de Django son por modelo (CRUD), no por caso de uso, y no modelan las habilitaciones comerciales por empresa |

## 2. Capas y reglas de dependencia

```
src/<contexto>/
├── domain/          # Entidades, value objects, servicios de dominio, errores. Python puro.
├── application/     # Casos de uso (1 clase/función por UC), DTOs, puertos (Protocol).
├── infrastructure/  # Modelos ORM, repositorios, adaptadores externos (PSE, email, storage).
└── interfaces/      # Vistas HTMX, forms, serializers DRF, URLs, comandos de gestión.
```

| Regla | Verificación |
|---|---|
| `domain` no importa `django`, `infrastructure` ni `interfaces` | import-linter (contrato `forbidden`) |
| `application` solo importa `domain` y puertos propios o de `shared` | import-linter (contrato `layers`) |
| Un contexto usa otro **solo** vía su `application` (fachada pública) | import-linter (contrato `independence` + excepciones explícitas) |
| `interfaces` no contiene reglas de negocio | Code review |

**Pragmatismo:** los catálogos CRUD sin reglas (categorías, unidades, almacenes, proveedores, categorías de gasto) pueden usar `ModelForm` directo en `interfaces` sin capa de dominio.

### Contextos y dependencias permitidas

```
tenancy  ◄── todos
catalog  ◄── inventory, purchasing, production, sales
inventory ◄── purchasing, production, sales, finance (lectura)
production ──► inventory, catalog, sales (PedidosPort: lectura + transiciones de pedido)
sales    ──► inventory, catalog, billing, production (ProduccionService.desvincular_pedido)
billing  ──► (ninguno de negocio; recibe DTOs)
finance  ──► sales, inventory, production, billing (consultas de lectura)
```

**Registro inverso hacia tenancy:** tenancy no conoce a los demás contextos. Cada contexto registra en `TenancyService`, desde su `AppConfig.ready()`, su `SembradorInicial` (datos iniciales de una empresa nueva, spec 001a) y sus `ContadorOperacionesEnCurso` (advertencia al quitar una funcionalidad, spec 001b).

La calculadora de tributos (IGV/ISC) vive en `sales/domain`; billing recibe los importes ya calculados en el `ComprobanteDTO`.

## 3. Shared kernel (`src/shared`)

| Componente | Responsabilidad |
|---|---|
| `Money` | Importe en PEN, `Decimal` con 2 decimales, redondeo `ROUND_HALF_UP` |
| `Quantity` | Cantidad `Decimal` con 4 decimales, `ROUND_HALF_UP`; no negativa salvo deltas explícitos |
| `UnitCost` | Costo unitario `Decimal` con 6 decimales, `ROUND_HALF_UP` |
| `TenantContext` | `contextvars.ContextVar[empresa_id]`; lo setea el middleware y los comandos de gestión |
| `UnitOfWork` (puerto) | Envuelve `transaction.atomic()`; un caso de uso = una transacción |
| `SequencePort` | `siguiente(documento, serie) -> int`; adaptador que llama a `fn_siguiente_correlativo` (§5.1) |
| `Clock` (puerto) | Fecha/hora actual en America/Lima; inyectable en tests |
| `DomainError` | Jerarquía de errores de negocio con código (`STOCK_INSUFICIENTE`, `ESTADO_INVALIDO`…) traducible a mensaje de UI |

## 4. Multi-tenancy

1. El middleware `TenantMiddleware` resuelve `empresa_id` desde `request.user` y lo fija en `TenantContext`. En la API (DRF), la clase de autenticación por token fija `TenantContext` y `request.actor` (el middleware corre antes de la autenticación DRF y no ve al usuario del token).
2. Los repositorios **siempre** filtran por `TenantContext.get()`; si no hay tenant lanzan `TenantNoDefinido`, **también para el super admin**. El super admin lee datos de una empresa solo con `with tenant_context(empresa_id):` explícito, y `all_tenants` solo se usa en las rutas `/plataforma/*`.
3. Los modelos de negocio heredan de `TenantModel` (abstracto): `empresa = FK`, índice compuesto y un manager `objects` que filtra por tenant + un `all_tenants` explícito solo para el super admin.
4. Las unicidades de negocio son siempre `UniqueConstraint(fields=["empresa", …])`.
5. Las vistas SQL (`vw_*`) se mapean como modelos `managed=False` que heredan de `TenantModel`. No se ejecuta SQL crudo fuera de los adaptadores de `infrastructure`, y ahí el `empresa_id` se toma siempre de `TenantContext`.
6. **Test de aislamiento único y parametrizado** (bloquea el release, PRD §7): recorre todas las subclases de `TenantModel` y todas las rutas con `<id>`; crea datos en la empresa B, los pide desde A y espera 404 / lista vacía / rechazo de referencia. Además, una ruta de tenant invocada por el super admin sin `tenant_context` no devuelve datos. Cubre a todas las épicas; no se reescribe por épica.

## 5. Persistencia

| Tema | Regla |
|---|---|
| Tipos | Cantidades `NUMERIC(14,4)`; costos unitarios `NUMERIC(14,6)`; importes `NUMERIC(14,2)` |
| Integridad | `CHECK (cantidad >= 0)` en `stock`; FK con `PROTECT` en documentos (no `CASCADE`) |
| Fechas | `USE_TZ=True`, `TIME_ZONE='America/Lima'`. Fechas de negocio de documentos (`fecha_emision`, `fecha_fin`, fecha de gasto) se guardan como `DATE` en hora de Lima; los instantes (`created_at`, `anulado_en`) como `timestamptz`. Los filtros por período sobre `timestamptz` usan rango semiabierto `[desde, hasta + 1 día)` evaluado `AT TIME ZONE 'America/Lima'` |
| Concurrencia: orden de locks | Locks de fila en este orden fijo (evita deadlocks): cabecera del documento → `secuencia` (vía `fn_siguiente_correlativo`) → `costo_producto` → `stock` (ordenados por `producto_id`, `almacen_id`, `lote_id`). El orden vale **para toda la transacción**, no por llamada: un caso de uso que hace varias llamadas a inventario numera primero y llama a `InventarioService.bloquear(productos)` antes de la primera salida o entrada |
| Concurrencia: transiciones | Todo caso de uso que cambia el estado de un agregado existente (anular, iniciar, terminar, confirmar, entregar) hace `select_for_update()` de la cabecera y **revalida el estado** antes de actuar. Un doble clic produce `EstadoInvalido`, nunca un doble efecto |
| Concurrencia: idempotencia | Una reversión de kardex se marca con `revierte_id`; `UNIQUE (revierte_id) WHERE revierte_id IS NOT NULL` impide revertir dos veces el mismo movimiento. Las claves de idempotencia que chocan (`IntegrityError`) devuelven el documento existente |
| Outbox | Un efecto externo que no puede perderse (emitir comprobante, anulación tributaria) se registra como fila `PENDIENTE` **dentro** de la transacción de negocio. `on_commit` solo hace un intento best-effort; el cron procesa lo que siga pendiente tomando filas con `select_for_update(skip_locked=True)` y un `pg_try_advisory_lock` por comando |
| Inmutabilidad | `movimiento` es solo de inserción; ni la app ni el admin permiten editar o borrar |
| Auditoría | `created_by`, `created_at`, `updated_at` en todos los modelos de negocio; `anulado_por`, `anulado_en` y `motivo_anulacion` en los documentos |
| Migraciones | Django migrations; seeds por empresa al crearla (almacén "Principal", unidades SUNAT, categorías de gasto) |

### 5.1 Objetos PL/pgSQL (ADR-10)

Se versionan como `migrations.RunSQL` (con `reverse_sql`) dentro de la app dueña de la tabla, en `infrastructure/sql/*.sql`.

| Objeto | Tipo | Propósito | Regla |
|---|---|---|---|
| `fn_siguiente_correlativo(p_empresa, p_documento, p_serie)` | Función | `INSERT … ON CONFLICT DO UPDATE SET ultimo_numero = ultimo_numero + 1 RETURNING ultimo_numero`: atómica, sin huecos por concurrencia dentro de la transacción. Implementa `SequencePort` | RN-GEN-06 |
| `trg_movimiento_inmutable` | Trigger `BEFORE UPDATE OR DELETE` en `inventory_movimiento` | `RAISE EXCEPTION` si se intenta modificar o borrar | RN-GEN-03 |
| `trg_documento_confirmado_inmutable` | Trigger `BEFORE UPDATE` en compras, envasados y ventas | Solo permite cambiar `estado` y los campos de anulación una vez confirmados. **No** se aplica a `production_op`, cuyos campos de resultado (`litros_reales`, costos, lote, `fecha_fin`) se completan al terminar; ahí la regla la aplica el caso de uso | RN-GEN-07 |
| `trg_tenant_consistente` | Trigger `BEFORE INSERT` en tablas de detalle | Las tablas de detalle **no** tienen `empresa_id` propio: heredan el tenant de su cabecera. El trigger verifica que el producto, lote o almacén referenciado por el detalle pertenezca a la misma empresa que la cabecera | RN-GEN-01 |
| `CHECK (cantidad >= 0)` en `inventory_stock` | Constraint | Última barrera contra stock negativo | RN-GEN-02 |
| `vw_kardex` | Vista | Kardex con nombres de producto, almacén, lote y usuario, lista para paginar | UC-INV-03 |
| `fn_estado_resultados(p_empresa, p_desde, p_hasta)` | Función `RETURNS TABLE` (`STABLE`) | Calcula ventas netas, costo, mermas, gastos y utilidades (fuente única para la UI, la exportación CSV y la API) | UC-FIN-03 |
| `vw_stock_valorizado` | Vista | Stock × costo promedio por producto, almacén y lote | UC-INV-02, UC-FIN-04 |

**Reglas de uso:**
- La lógica de negocio (cálculo de costo promedio, FEFO, envasado, transiciones de estado) **no** va en PL/pgSQL. Si un trigger rechaza una operación, es un bug del dominio: se registra como error 500 y se agrega un test.
- Los errores de trigger usan `ERRCODE` propio (clase `P0`) para distinguirlos en los logs.
- Cada objeto SQL tiene un test de integración (`pytest-django` + PostgreSQL real) que verifica el rechazo o el resultado esperado.

## 6. Manejo de errores y UX de errores

- Los errores de dominio se muestran al usuario con mensaje en español y código; no se registran como error 500.
- Los errores de infraestructura (PSE caído) se registran en log y no revierten la operación de negocio cuando el spec lo indica (ver E07).

## 7. Estrategia de testing

| Nivel | Herramienta | Alcance | Meta |
|---|---|---|---|
| Unitario de dominio | pytest | Costo promedio, cálculo de envasado, FEFO, transiciones de estado, tributos | 100 % de las reglas RN-* cubiertas |
| Caso de uso | pytest + repositorios en memoria (fakes) | Cada UC-* con sus errores | Todos los UC |
| Integración | pytest-django + PostgreSQL | Repositorios, locks, aislamiento de tenant, constraints | Todos los repositorios |
| Aceptación | pytest-bdd sobre `features/*.feature` | Escenarios `@critico` ejecutados end-to-end por la capa application | 100 % de `@critico` en verde para release |
| Contrato externo | Adaptador PSE contra su sandbox | Emisión, consulta, anulación | Antes del go-live |

Mapeo: cada escenario Gherkin lleva el tag `@UC-*`; cada test de dominio referencia la regla `RN-*` en su nombre o docstring.

## 8. CI

`ruff check` · `ruff format --check` · `lint-imports` · `pytest --cov` (umbral a definir) · `python manage.py makemigrations --check`.

## 9. Despliegue (MVP)

Docker Compose: `web` (gunicorn), `db` (PostgreSQL 16), `cron` (comandos de facturación). Almacenamiento de XML/CDR/PDF/logos en volumen local o almacenamiento de objetos compatible con S3 (por definir en T1, **antes de S4**). XML y CDR son documentos con plazo legal de conservación: el almacenamiento elegido debe tener respaldo, y las descargas se sirven solo a través de vistas con chequeo de tenant (nunca por URL pública).

**Seguridad (PRD §7):** `SECURE_SSL_REDIRECT=True`, HSTS, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, `SESSION_COOKIE_AGE` y expiración por inactividad según Q6.

**Rendimiento (PRD §7):** paginación por defecto en todos los listados de la UI y en DRF (`PAGE_SIZE=25`; cursor en kardex). Antes del go-live, test de carga con el volumen del PRD (10 000 productos, 100 000 movimientos) contra el objetivo p95 < 800 ms.

## 10. Preguntas abiertas técnicas

| # | Pregunta |
|---|---|
| T1 | Hosting objetivo (VPS, GCP, AWS) y almacenamiento de archivos |
| T2 | Umbral de cobertura en CI |
| T3 | ¿Se habilita Row-Level Security de PostgreSQL como segunda barrera de aislamiento en el MVP? |
