# MEMORY.md — Estado del proyecto

> Se actualiza al terminar cada fase SDD (AGENTS.md §2). Última actualización: 2026-10-10.

## Fase actual

**Clarificación.** Las 22 specs (8 épicas divididas en partes, formato `NNNNx-Modulo-nombre`) están en EARS y en `borrador`, esperando las respuestas de las dudas `[NECESITA ACLARACIÓN]` y la aprobación del PO. No hay código. Todas tienen un `tasks.md` **de ejemplo** (283 tareas en total), que no se ejecuta hasta aprobar spec y plan.

| Spec | spec.md | plan.md | tasks.md | Bloqueos |
|---|---|---|---|---|
| 0000 Arquitectura | — | borrador | — | T1 (almacenamiento), T2, T3 |
| [0001a](specs/0001a-Tenancy-registro-sesion/) Registro, sesión y suscripción | borrador (16 RF) | borrador | ejemplo (26 tareas) | Q6 |
| [0001b](specs/0001b-Tenancy-plataforma-habilitaciones/) Plataforma: planes y habilitaciones | borrador (13 RF) | borrador | ejemplo (16 tareas) | Q8 |
| [0001c](specs/0001c-Tenancy-usuarios-roles/) Usuarios, roles y permisos | borrador (18 RF) | borrador | ejemplo (22 tareas) | — |
| [0001d](specs/0001d-Tenancy-auditoria-tokens/) Auditoría de accesos y tokens de API | borrador (7 RF) | borrador | ejemplo (11 tareas) | — |
| [0002a](specs/0002a-Catalogo-productos/) Catálogo: unidades y productos | borrador (17 RF) | borrador | ejemplo (16 tareas) | Q7, maquila |
| [0002b](specs/0002b-Catalogo-presentaciones/) Catálogo: presentaciones y materiales | borrador (4 RF) | borrador | ejemplo (8 tareas) | — |
| [0002c](specs/0002c-Catalogo-isc/) Catálogo: categorías y tarifas de ISC | borrador (7 RF) | borrador | ejemplo (9 tareas) | código ISC (01 vs 02) |
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

- Stack Python/Django/PostgreSQL con pytest (la plantilla SDD original decía `node --test`; se adaptó).
- Specs en formato EARS; los `.feature` se mantienen como criterio de aceptación ejecutable.
- Venta anulada pasa a `ANULADA` de inmediato; la NC espera a que el comprobante original sea aceptado (propuesta, falta visto bueno del contador).
- Tipo `MERCADERIA` dentro del MVP.
- **E01 completo en S0** (Q11): planes, ajustes con vigencia y vista previa de impacto. Excepción aprobada al art. 7.6 de la constitución, documentada en la spec 001b.

## Pendientes del PO / contador

- **Q1** PSE · **Q3** taproom B2C · **Q6** sesión y contraseñas · **Q7** vida útil · **Q8** planes · **Q10** lote perdido · **Q12** consultas al contador.
- **Código de tipo de sistema ISC:** el contador dijo `01`; el catálogo 08 de SUNAT indica `02` para monto fijo → validar en el sandbox del PSE.
- **Cerveza que entra sin producir:** ¿maquila o compra a granel? Hoy solo se cubre la reventa de terceros (`MERCADERIA`) y el saldo inicial. ¿La reventa de cerveza de terceros paga ISC otra vez? (contador).

## Próximo paso

1. Resolver las dudas `[NECESITA ACLARACIÓN]` (priorizar Q10, que cambia el alcance de S2, y Q6/Q8, que bloquean las specs 0001a y 0001b).
2. Aprobar cada `spec.md` en orden de dependencia (0001a → 0001d en S0; luego 0002a, 0003a…).
3. Revisar y aprobar su `plan.md` (ya escritos en borrador).
4. Recién entonces revisar y aprobar su `tasks.md` (hoy son ejemplos en borrador).
