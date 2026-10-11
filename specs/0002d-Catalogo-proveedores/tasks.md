# Tareas 0002d — Catálogo: proveedores y proveedores del producto

Estado: borrador (2026-10-10), pendiente de aprobación del PO.

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8): una tarea a la vez, test primero, y `ruff check`, `ruff format --check`, `lint-imports` y `makemigrations --check` en verde.

- [ ] **T1. Mover `Ruc` a `shared/domain/documentos.py` y agregar DNI.** — RF-COM-01
  - Hecho cuando: tenancy usa `Ruc` desde `shared` con sus tests en verde, y un test valida DNI de 8 dígitos.
- [ ] **T2. Crear el contexto `purchasing` (app, capas y contratos de import-linter).** — —
  - Hecho cuando: `lint-imports` está en verde con los contratos nuevos.
- [ ] **T3. Implementar `validar_documento()` y `validar_proveedor_producto()`.** — RF-COM-01, RF-COM-21
  - Hecho cuando: `test_proveedor.py` está en verde.
- [ ] **T4. Crear los modelos de proveedor y proveedor del producto con sus constraints.** — RF-COM-01, RF-COM-21
  - Hecho cuando: un test comprueba el documento único por empresa y los `CHECK` de precio y plazo.
- [ ] **T5. Crear los casos de uso de proveedores y el puerto `ComprasPort`.** — RF-COM-01 a RF-COM-03
  - Hecho cuando: "Registrar un proveedor", "Proveedor con compras se desactiva en vez de eliminarse" y "Documento inválido" están en verde.
- [ ] **T6. Crear `AsociarProveedorProducto` y `QuitarProveedorProducto`.** — RF-COM-21, RF-COM-22
  - Hecho cuando: "Asociar un proveedor a un insumo" y "Un proveedor desactivado no se asocia" están en verde.
- [ ] **T7. Crear `/compras/proveedores/` y la pestaña "Compras" de la ficha.** — RF-COM-01 a RF-COM-03, RF-COM-22
  - Hecho cuando: "Un producto que no se compra no tiene pestaña Compras" está en verde y el meta-test de aislamiento cubre las rutas nuevas.
- [ ] **T8. Verificar la spec completa.** — RF-COM-01 a RF-COM-03, RF-COM-21, RF-COM-22
  - Hecho cuando: suite, lint, contratos y migraciones en verde; cada RF con escenario o test; `MEMORY.md` actualizado.
