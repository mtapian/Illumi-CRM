# MEMORY.md — Estado del proyecto

> Se actualiza al terminar cada fase SDD (AGENTS.md §2). Última actualización: 2026-10-10.

## Fase actual

**Clarificación.** Las 8 specs están en formato EARS y en `borrador`, esperando las respuestas de las dudas `[NECESITA ACLARACIÓN]` y la aprobación del PO. No hay código ni `tasks.md`.

| Spec | spec.md | plan.md | tasks.md | Bloqueos |
|---|---|---|---|---|
| 000 Arquitectura | — | borrador | — | T1 (almacenamiento), T2, T3 |
| 001 Tenancy y accesos | borrador (EARS, 54 RF) | borrador (formato SDD, 100 % RF cubiertos) | — | Q6, Q8 |
| 002 Catálogo | borrador (EARS, 28 RF) | borrador (formato SDD, 100 % RF cubiertos) | — | Q7, maquila (ver pendientes) |
| 003 Inventario | borrador (EARS, 25 RF) | borrador (formato SDD, 100 % RF cubiertos) | — | Q12 (anulación de compra consumida) |
| 004 Compras | borrador (EARS, 20 RF) | borrador (formato SDD, 100 % RF cubiertos) | — | maquila / compra de granel |
| 005 Producción | borrador (EARS, 34 RF) | borrador (formato SDD, 100 % RF cubiertos) | — | Q10, Q12 (costeo del granel) |
| 006 Ventas y pedidos | borrador (EARS, 42 RF) | borrador (formato SDD, 100 % RF cubiertos) | — | Q3 |
| 007 Facturación electrónica | borrador (EARS, 32 RF) | borrador (formato SDD, 100 % RF cubiertos) | — | Q1 (PSE), código de tipo de sistema ISC |
| 008 Finanzas | borrador (EARS, 16 RF) | borrador (formato SDD, 100 % RF cubiertos) | — | Q10 |

## Historial

- **2026-10-10 — Validación de alcance y specs.** Revisión en 3 frentes (producto, dominio SUNAT/costeo, arquitectura). 10 bloqueantes; corregidos los de modelo (valor total en costo promedio, outbox de comprobantes, locks de anulación, cuotas a crédito, merma de envasado, tablas base de 001). Specs pasadas a revisión.
- **2026-10-10 — ISC resuelto (Q2)** con el contador: Sistema Específico, S/ 2.51 por litro desde el 2024-07-01; base del IGV = valor + ISC; NC ajusta en proporción; entregas gratuitas = retiro de bienes, su costo y los tributos asumidos van a gastos de venta. ISC configurable por empresa con categorías y tarifas por vigencia (spec 002 UC-CAT-05).
- **2026-10-10 — Mercadería (Q13):** el PO confirma la reventa (agua, snacks, merchandising). Nuevo tipo `MERCADERIA`: se compra y se vende sin producir; lote opcional.
- **2026-10-10 — Estructura SDD:** carpetas `specs/NNN-nombre/` con `spec.md` / `plan.md` / `features/`; guía de trabajo en `AGENTS.md`; plantilla SDD adaptada a pytest y movida a `.claude/skills/sdd/`; `CLAUDE.md` importa `AGENTS.md` y `MEMORY.md`. Respaldo previo en el scratchpad de la sesión.
- **2026-10-10 — Constitución v1.0.0 ratificada** en `docs/constitution.md` (9 artículos), separada de `AGENTS.md`, que queda como guía operativa. `CLAUDE.md` importa los tres archivos.
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
- **E01 completo en S0** (Q11): planes, ajustes con vigencia y vista previa de impacto. Excepción aprobada al art. 7.6 de la constitución, documentada en la spec 001.

## Pendientes del PO / contador

- **Q1** PSE · **Q3** taproom B2C · **Q6** sesión y contraseñas · **Q7** vida útil · **Q8** planes · **Q10** lote perdido · **Q12** consultas al contador.
- **Código de tipo de sistema ISC:** el contador dijo `01`; el catálogo 08 de SUNAT indica `02` para monto fijo → validar en el sandbox del PSE.
- **Cerveza que entra sin producir:** ¿maquila o compra a granel? Hoy solo se cubre la reventa de terceros (`MERCADERIA`) y el saldo inicial. ¿La reventa de cerveza de terceros paga ISC otra vez? (contador).

## Próximo paso

1. Resolver las dudas `[NECESITA ACLARACIÓN]` (priorizar Q10, que cambia el alcance de S2, y Q6/Q8, que bloquean la spec 001).
2. Aprobar cada `spec.md` (empezando por 001, que va en S0).
3. Revisar y aprobar su `plan.md` (ya escritos en borrador).
4. Recién entonces escribir `tasks.md`.
