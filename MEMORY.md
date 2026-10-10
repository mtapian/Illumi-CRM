# MEMORY.md — Estado del proyecto

> Se actualiza al terminar cada fase SDD (AGENTS.md §2). Última actualización: 2026-10-10.

## Fase actual

**Implementación** de las épicas 0001 (0001a–0001d) y 0002 (0002a–0002c) completas. El resto sigue en **Clarificación**; la siguiente es 0003a, que primero necesita aprobar su spec, plan y tareas.

Las 22 specs usan el formato `NNNNx-Modulo-nombre`. Las que no están aprobadas siguen en `borrador`, esperando respuestas a sus `[NECESITA ACLARACIÓN]`; sus `tasks.md` son ejemplos.

| Spec | spec.md | plan.md | tasks.md | Bloqueos |
|---|---|---|---|---|
| 0000 Arquitectura | — | aprobado | — | T1 (almacenamiento), T2, T3 |
| [0001a](specs/0001a-Tenancy-registro-sesion/) Registro, sesión y suscripción | **implementada** (16 RF) | implementado | 26/26 ✔ | 2 escenarios parciales (dependen de 0003a, 0006b, 0008a) |
| [0001b](specs/0001b-Tenancy-plataforma-habilitaciones/) Plataforma: planes y habilitaciones | **implementada** (13 RF) | implementado | 16/16 ✔ | — (contador de OP en curso: falso hasta 0005) |
| [0001c](specs/0001c-Tenancy-usuarios-roles/) Usuarios, roles y permisos | **implementada** (18 RF) | implementado | 22/22 ✔ | 8 escenarios parciales (acciones de 0002a, 0003b/c, 0004a, 0006, 0008) |
| [0001d](specs/0001d-Tenancy-auditoria-tokens/) Auditoría de accesos y tokens de API | **implementada** (7 RF) | implementado | 11/11 ✔ | 1 escenario parcial (consulta de stock, 0003c) |
| [0002a](specs/0002a-Catalogo-productos/) Catálogo: unidades y productos | **implementada** (17 RF) | implementado | 16/16 ✔ | 1 escenario parcial (compras 0004a, recetas 0005a); maquila sigue abierta |
| [0002b](specs/0002b-Catalogo-presentaciones/) Catálogo: presentaciones y materiales | **implementada** (4 RF) | implementado | 8/8 ✔ | 1 escenario parcial (costo promedio, 0003a) |
| [0002c](specs/0002c-Catalogo-isc/) Catálogo: categorías y tarifas de ISC | **implementada** (7 RF) | implementado | 9/9 ✔ | código ISC (01 vs 02): dato de la categoría |
| [0003a](specs/0003a-Inventario-movimientos-costo/) Inventario: almacenes, movimientos y costo promedio | borrador (11 RF) | borrador | ejemplo (17 tareas) | Q12 |
| [0003b](specs/0003b-Inventario-ajustes/) Inventario: ajustes | borrador (7 RF) | borrador | ejemplo (9 tareas) | Q12 (sustento de mermas) |
| [0003c](specs/0003c-Inventario-consultas-alertas/) Inventario: stock, kardex y alertas | borrador (7 RF) | borrador | ejemplo (9 tareas) | — |
| [0004a](specs/0004a-Compras-proveedores-registro/) Compras: proveedores y registro de compras | borrador (16 RF) | borrador | ejemplo (12 tareas) | Q12, maquila |
| [0004b](specs/0004b-Compras-anulacion/) Compras: anulación | borrador (4 RF) | borrador | ejemplo (6 tareas) | Q12 |
| [0005a](specs/0005a-Produccion-recetas-op/) Producción: recetas y órdenes de producción | borrador (19 RF) | borrador | ejemplo (15 tareas) | Q10, Q12 |
| [0005b](specs/0005b-Produccion-envasado-cierre/) Producción: envasado, cierre y costo del lote | borrador (15 RF) | borrador | ejemplo (13 tareas) | Q12, wireframes |
| [0006a](specs/0006a-Ventas-clientes-pedidos/) Ventas: clientes y pedidos | borrador (19 RF) | borrador | ejemplo (15 tareas) | wireframe del tablero |
| [0006b](specs/0006b-Ventas-registro-venta/) Ventas: registro de la venta | borrador (16 RF) | borrador | ejemplo (15 tareas) | Q3 |
| [0006c](specs/0006c-Ventas-anulacion-correccion/) Ventas: anulación y corrección de cliente | borrador (7 RF) | borrador | ejemplo (9 tareas) | contador (RF-VEN-32) |
| [0007a](specs/0007a-Facturacion-configuracion-emision/) Facturación: configuración y emisión | borrador (14 RF) | borrador | ejemplo (15 tareas) | Q1, T1, código ISC |
| [0007b](specs/0007b-Facturacion-reintentos-resumen/) Facturación: reintentos y resumen diario | borrador (9 RF) | borrador | ejemplo (10 tareas) | Q1, Q12 |
| [0007c](specs/0007c-Facturacion-notas-credito-descargas/) Facturación: notas de crédito y descargas | borrador (9 RF) | borrador | ejemplo (9 tareas) | contador (RF-FAC-25) |
| [0008a](specs/0008a-Finanzas-gastos/) Finanzas: gastos operativos | borrador (5 RF) | borrador | ejemplo (8 tareas) | Q12 |
| [0008b](specs/0008b-Finanzas-resultados-reportes/) Finanzas: estado de resultados, dashboard y exportación | borrador (11 RF) | borrador | ejemplo (13 tareas) | Q10 |

## Historial

- **2026-10-10 — Implementación de la épica 0002** (orden del PO: "continuar con 0002"). Nuevo contexto `catalog` (hexagonal; import-linter con 5 contratos, incluido que tenancy no conoce al catálogo). 0002a: unidades sembradas al registrar, familias, productos por tipo con validación en el dominio y `CHECK` en la base, límite del plan, desactivar/eliminar según stock y referencias, listado con filtros (p95 < 800 ms con 10 000), API `GET /api/v1/productos/`. 0002b: presentación de cada terminado (granel, contenido, materiales con 4 decimales) creada junto con el producto; contenido bloqueado con movimientos; `materiales_para()` para 0005b. 0002c: categorías de ISC con tarifas por vigencia de solo inserción (trigger); `isc_aplicable()` / `isc_de_linea()` para 0006b y 0007a. Inventario se consulta por un puerto (`catalog.application.puertos`) que llena la épica 0003. 327 tests en verde, 12 escenarios parciales con motivo.
- **2026-10-10 — Implementación de 0001b, 0001c y 0001d** (orden del PO: "procede con todo 0001"). 0001b: catálogo de accesos como código (`shared/domain/accesos.py`) sincronizado con la BD en cada `migrate`; planes con funcionalidades y vista previa de impacto; ajustes por empresa con vigencia; suspender/reactivar al estado anterior; pantallas `/plataforma/*`. 0001c: roles por empresa con plantillas iniciales (sembrador), permisos efectivos recalculados en cada request (`AccesoMiddleware` + `Actor`), `CasoDeUso` con permiso obligatorio y meta-tests de autorización y aislamiento, control de escalada, último administrador con lock, menú filtrado por permisos, pantallas `/usuarios/` y `/roles/`. 0001d: auditoría de accesos inmutable (trigger), tokens de API con hash SHA-256 mostrados una sola vez, usuario técnico, autenticación DRF por token (`VistaApi`), pantallas `/auditoria/accesos/` y `/integracion/tokens/`. Se agrega `djangorestframework==3.16.1`. 241 tests en verde, 10 escenarios parciales con motivo. Desde ahora `/configuracion/empresa/` exige `core.empresa.gestionar` (pendiente de 0001a). **Inconsistencia a revisar por el PO:** el escenario "El Administrador recibe automáticamente lo que se habilita después" agrega "Órdenes de producción" sola, pero RN-TEN-09 exige "Recetas"; el paso de prueba agrega ambas.
- **2026-10-10 — Aprobación e implementación de 0001a.** El PO aprueba 0001a–0001d y 0002a–0002c (spec, plan y tareas) con los valores por defecto: Q6 = 5 intentos / 15 min y sesión de 8 h de inactividad (las 8 h las propuso Claude: confirmar); Q8 = el plan de prueba incluye todo; Q7 = vida útil por presentación; código ISC = dato configurable. Se implementa **solo 0001a** (26 tareas, test primero): proyecto Django 5.2, import-linter con 3 contratos, pytest-bdd sobre `specs/*/features`, `TenantContext`/`TenantModel`, `fn_siguiente_correlativo`, triggers de inmutabilidad, registro con sembradores, login con bloqueo, recuperación por outbox de correos, configuración de empresa con IGV con vigencia, middlewares de tenant y suscripción, cron `vencer_suscripciones`, aviso de vencimiento. 94 tests en verde, 2 escenarios parciales. **Desvío del art. 7.1 aprobado por el PO:** Python 3.13 local (no 3.12); PostgreSQL 16 en Docker (`docker-compose.yml`, puerto 54320).
- **2026-10-10 — Todas las épicas divididas y renombradas** al formato `NNNNx-Modulo-nombre` pedido por el PO (`0000-Arquitectura`, `0001a-Tenancy-…` … `0008b-Finanzas-…`): 22 specs, 251 RF sin pérdidas ni duplicados (verificado por script). Cada parte tiene `spec.md`, `plan.md`, `tasks.md` de ejemplo y sus escenarios; las referencias "spec 00N" pasan a "épica 000N". Escenarios nuevos para RF que no tenían: tokens de API (RF-TEN-45 a 48, 54), escalada (RF-TEN-53), usuarios no se borran (RF-TEN-13), lotes y factura en compras (RF-COM-07, 19, 20, bonificación), anular OP con pedidos (RF-PRD-19), pedido sin OP activa (RF-VEN-41), corrección no aceptada (RF-VEN-40), reintentos simultáneos (RF-FAC-17), rechazados sin reemitir (RF-FAC-32), pendientes tributarios (RF-FIN-12) y exportación sin costos (RF-FIN-16). Sembradores iniciales y `PedidosPort` aparecen como tareas en cada parte. Respaldo de las carpetas originales en el scratchpad.
- **2026-10-10 — Validación de alcance y specs.** Revisión en 3 frentes (producto, dominio SUNAT/costeo, arquitectura). 10 bloqueantes; corregidos los de modelo (valor total en costo promedio, outbox de comprobantes, locks de anulación, cuotas a crédito, merma de envasado, tablas base de 001). Specs pasadas a revisión.
- **2026-10-10 — ISC resuelto (Q2)** con el contador: Sistema Específico, S/ 2.51 por litro desde el 2024-07-01; base del IGV = valor + ISC; NC ajusta en proporción; entregas gratuitas = retiro de bienes, su costo y los tributos asumidos van a gastos de venta. ISC configurable por empresa con categorías y tarifas por vigencia (hoy spec 0002c, UC-CAT-05).
- **2026-10-10 — Mercadería (Q13):** el PO confirma la reventa (agua, snacks, merchandising). Nuevo tipo `MERCADERIA`: se compra y se vende sin producir; lote opcional.
- **2026-10-10 — Estructura SDD:** carpetas `specs/NNN-nombre/` con `spec.md` / `plan.md` / `features/`; guía de trabajo en `AGENTS.md`; plantilla SDD adaptada a pytest y movida a `.claude/skills/sdd/`; `CLAUDE.md` importa `AGENTS.md` y `MEMORY.md`. Respaldo previo en el scratchpad de la sesión.
- **2026-10-10 — Constitución v1.0.0 ratificada** en `docs/constitution.md` (9 artículos), separada de `AGENTS.md`, que queda como guía operativa. `CLAUDE.md` importa los tres archivos.
- **2026-10-10 — Spec 001 dividida en 4** (001a registro y sesión → 001b plataforma → 001c usuarios y roles → 001d auditoría y tokens), porque su `tasks.md` de ejemplo salió con 65 tareas (la skill `sdd` pide dividir si hay más de 10). Los RF conservan su número (RF-TEN-NN) y la épica sigue siendo E01 (etiquetas `@E01a`…`@E01d`). Se agregan dos puertos de registro inverso hacia tenancy: `SembradorInicial` (001a) y `ContadorOperacionesEnCurso` (001b). Cada subspec tiene un `tasks.md` de ejemplo en borrador. Respaldo de la 001 original en el scratchpad.
- **2026-10-10 — Etiquetas `@RF-…` en los escenarios** de las 8 specs (regla en AGENTS.md §3). 198/251 RF tienen escenario; los 53 restantes se cubren solo con tests del plan §7.
- **2026-10-10 — Planes 001–008 regenerados** con el formato pedido por el PO: archivos y responsabilidades, modelo de datos, funciones puras (con `hoy` como parámetro cuando depende de la fecha), algoritmos clave en pseudocódigo, interfaz, decisiones con alternativa descartada, tests con pytest (no `node --test`, por la constitución art. 7.1) y tabla de cobertura RF → partes. Verificado por script: los 251 RF están cubiertos. Estado: borrador.
- **2026-10-10 — Validación y ajuste de specs (58 hallazgos).** Resueltos 57: ambigüedades, contradicciones (transiciones del pedido, gratuitas vs. ISC, facturación deshabilitada vs. reintentos, costos visibles, anulación de gastos), casos límite (escalada de privilegios, tokens de empresas suspendidas, FEFO sin vencimiento, lote con otro vencimiento, varias OP por pedido, devolución parcial, etc.) y conflictos con la constitución. Nuevo UC-VEN-08 (corregir cliente con NC `02` sin mover stock); nuevo permiso `catalogo.isc.gestionar`; parámetros tributarios con vigencia. Constitución enmendada a **v1.1.0** (arts. 3.1, 4.5, 5.2, 6.2). Planes y features sincronizados. #58 (Q11) resuelto por el PO: E01 completo.
- **2026-10-10 — Plantilla de spec del PO aplicada** a las 8 specs: secciones de la plantilla + `Definiciones` opcional y línea `Estado:`; historias `H1:`, requisitos `RF-<MÓD>-NN:`; sin tabla de metadatos ni tabla de RN (cada RF cita su `RN-*`). Plantilla de la skill `sdd` actualizada.
- **2026-10-10 — Specs 001–008 convertidas a EARS** (240 RF en total).  Las dudas pasaron a `[NECESITA ACLARACIÓN]` en cada spec.

## Decisiones tomadas (no reabrir sin el PO)

- Un `TERMINADO` se crea con su presentación en la misma transacción (RF-CAT-05).
- Supuestos de las plantillas de rol (0001c, la tabla no los detalla): "stock y kardex" incluye lotes; Gerente y Almacén gestionan almacenes; "Compras" incluye proveedores. Confirmar con el PO.
- Guía visual de la UI: la imagen de `Referencia:html/` (ADR-12 en el plan 0000). Aplicada a las pantallas de 0001a el 2026-10-10.
- Entorno de desarrollo: Python 3.13 local + PostgreSQL 16 en Docker (desvío temporal del art. 7.1, aprobado por el PO el 2026-10-10).
- Implementación una spec a la vez; Claude para al terminar cada spec y espera la orden del PO.
- Stack Python/Django/PostgreSQL con pytest (la plantilla SDD original decía `node --test`; se adaptó).
- Specs en formato EARS; los `.feature` se mantienen como criterio de aceptación ejecutable.
- Venta anulada pasa a `ANULADA` de inmediato; la NC espera a que el comprobante original sea aceptado (propuesta, falta visto bueno del contador).
- Tipo `MERCADERIA` dentro del MVP.
- **E01 completo en S0** (Q11): planes, ajustes con vigencia y vista previa de impacto. Excepción aprobada al art. 7.6 de la constitución, documentada en la spec 001b.

## Pendientes del PO / contador

- **Formato de decimales en pantalla:** hoy coma (es-pe de Django: 2,51). ¿Punto, como se usa en Perú?
- **Q1** PSE · **Q3** taproom B2C · **Q6** sesión y contraseñas · **Q7** vida útil · **Q8** planes · **Q10** lote perdido · **Q12** consultas al contador.
- **Código de tipo de sistema ISC:** el contador dijo `01`; el catálogo 08 de SUNAT indica `02` para monto fijo → validar en el sandbox del PSE.
- **Cerveza que entra sin producir:** ¿maquila o compra a granel? Hoy solo se cubre la reventa de terceros (`MERCADERIA`) y el saldo inicial. ¿La reventa de cerveza de terceros paga ISC otra vez? (contador).

## Próximo paso

1. Resolver las dudas `[NECESITA ACLARACIÓN]` (priorizar Q10, que cambia el alcance de S2, y Q6/Q8, que bloquean las specs 0001a y 0001b).
2. Aprobar cada `spec.md` en orden de dependencia (0001a → 0001d en S0; luego 0002a, 0003a…).
3. Revisar y aprobar su `plan.md` (ya escritos en borrador).
4. Recién entonces revisar y aprobar su `tasks.md` (hoy son ejemplos en borrador).
