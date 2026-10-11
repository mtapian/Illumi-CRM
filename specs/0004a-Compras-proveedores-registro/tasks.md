# Tareas 0004a — Compras: registro de compras

Estado: implementadas (aprobadas por el PO el 2026-10-11).

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8): una tarea a la vez, test primero, y `ruff check`, `ruff format --check`, `lint-imports` y `makemigrations --check` en verde.

- [x] **T1. Dominio: `validar_linea`, `separa_igv`, `totales`, `validar_documento_compra` y `validar_guia`.** — RF-COM-04, RF-COM-08, RF-COM-09, RF-COM-20, RF-COM-27
  - Hecho cuando: `test_compra.py` cubre bonificación, costo 0 sin bonificación, factura con DNI, guía de remisión válida e inválida y los totales del escenario de factura (1270.00 + 228.60 = 1498.60).
- [x] **T2. Modelos `Compra` y `CompraLinea` con constraints, índice único parcial del documento y trigger.** — RF-COM-04, RF-COM-11, RF-COM-13
  - Hecho cuando: un test comprueba el documento único entre compras activas (no en `SIN_DOCUMENTO`), los CHECK de costo y bonificación, y que una línea no se edita.
- [x] **T3. `IgvPort`, `CrearCompra`, `EditarCompra` y `PasarAEnProceso` (sin stock).** — RF-COM-04, RF-COM-05, RF-COM-08, RF-COM-23, RF-COM-25
  - Hecho cuando: crear y editar una compra no generan movimientos, "No se compra un bien que no se compra" y "No se compra a un proveedor desactivado" están en verde, y una compra no vuelve de En proceso a Creada.

- [x] **T3b. `FinalizarCompra` con revalidación y entrada de inventario.** — RF-COM-10, RF-COM-12, RF-COM-26, RF-COM-27
  - Hecho cuando: "Compra con factura separa el IGV del costo", "Compra con boleta no separa IGV" y "Solo al finalizar entra el stock" y "La fecha de la compra es referencia y no impide finalizar" , "Se finaliza con la fecha de recepción" y "Al confirmar la recepción se cambia el almacén y se registra la guía" están en verde, y una compra Finalizada no se edita ni se finaliza dos veces.
- [x] **T4. Lotes, documento duplicado y bonificación en la compra.** — RF-COM-06, RF-COM-07, RF-COM-11, RF-COM-19
  - Hecho cuando: los escenarios de lote, documento duplicado y bonificación están en verde.
- [x] **T5. `ComprasOrm.tiene_compras` en el puerto de 0002d.** — RF-COM-24
  - Hecho cuando: un proveedor con una compra registrada no se puede eliminar (el escenario de 0002d corre con una compra real).
- [x] **T6. Pantalla de compra con líneas dinámicas, totales en vivo y barra de estados (Creada ▸ En proceso ▸ Finalizada).** — RF-COM-04 a RF-COM-12, RF-COM-25, RF-COM-26
  - Hecho cuando: un test de vista crea una compra de 3 líneas, la edita, la pasa a en proceso y la finaliza; si se rechaza, las líneas vuelven.
- [x] **T7. Listado y detalle de compras; enlace desde el kardex.** — RF-COM-13, RF-COM-14
  - Hecho cuando: los filtros funcionan, el detalle de otra empresa da 404 (ruta en la prueba de aislamiento) y el kardex enlaza cada entrada `COMPRA`.
- [x] **T8. Verificar la spec completa.** — RF-COM-04 a RF-COM-14, RF-COM-19, RF-COM-20, RF-COM-23 a RF-COM-27
  - Hecho cuando: suite, lint, contratos y migraciones en verde; cada RF con escenario o test; `MEMORY.md` actualizado.
