# Tareas 0004b — Compras: anulación

Estado: borrador. Propuesta del 2026-10-11, pendiente de aprobación del PO junto con spec y plan.

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8): una tarea a la vez, test primero, y `ruff check`, `ruff format --check`, `lint-imports` y `makemigrations --check` en verde.

- [ ] **T1. Campos de anulación en la compra (migración y CHECK).** — RF-COM-15, RF-COM-28, RF-COM-29
  - Hecho cuando: un test comprueba que una compra Anulada exige motivo y fecha.
- [ ] **T2. `AnularCompra`: Finalizada revierte, Creada o En proceso solo cambia de estado.** — RF-COM-15, RF-COM-18, RF-COM-28, RF-COM-29
  - Hecho cuando: "Anular una compra finalizada revierte el stock al mismo costo" y "Anular una compra creada no mueve stock" están en verde y el documento se puede registrar de nuevo.
- [ ] **T3. Rechazo con el SKU consumido.** — RF-COM-16
  - Hecho cuando: "No se anula una compra cuyo stock ya se consumió" está en verde y la compra sigue Finalizada.
- [ ] **T4. Doble anulación concurrente y permiso.** — RF-COM-17, RF-COM-15
  - Hecho cuando: el test con dos hilos registra una sola reversión y "El rol Almacén no puede anular" está en verde.
- [ ] **T5. "Anular" con motivo en el detalle de la compra.** — RF-COM-15, RF-COM-16, RF-COM-28
  - Hecho cuando: un test de vista anula con motivo, muestra el rechazo con el producto y quién anuló.
- [ ] **T6. Verificar la spec completa.** — RF-COM-15 a RF-COM-18, RF-COM-28, RF-COM-29
  - Hecho cuando: suite, lint, contratos y migraciones en verde; cada RF con escenario o test; `MEMORY.md` actualizado.
