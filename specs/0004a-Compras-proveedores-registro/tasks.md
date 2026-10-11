# Tareas 0004a — Compras: proveedores y registro de compras

Estado: borrador (ejemplo). **No ejecutar:** `spec.md` y `plan.md` siguen en borrador (constitución, art. 2.1). Depende de Q12 y de la decisión sobre maquila.

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Dominio puro

- [ ] **T1. Implementar `es_comprable()`, `separa_igv()` y `validar_documento()`.** — RF-COM-05, RF-COM-08, RF-COM-20
  - Hecho cuando: `test_compra.py` comprueba que solo `INSUMO`, `ENVASE` y `MERCADERIA` se compran, que solo `FACTURA` separa IGV y que una factura con proveedor DNI se rechaza.

- [ ] **T2. Implementar `validar_linea()`, `vencimiento_sugerido()` y `resolver_lote()`.** — RF-COM-04, RF-COM-06, RF-COM-07, RF-COM-19
  - Hecho cuando: un test comprueba cantidad > 0, costo 0 solo con bonificación, lote exigido si el producto lo controla, y las tres acciones de `resolver_lote` (sumar, crear, error).

- [ ] **T3. Implementar `totales()` y `validar_fecha()`.** — RF-COM-08, RF-COM-09, RF-COM-12
  - Hecho cuando: `test_totales.py` reproduce 1270,00 / 228,60 / 1498,60 y la boleta de 59,00; una fecha de mañana se rechaza.

## Persistencia

- [ ] **T4. Crear los modelos de compra y línea de compra, con el índice único parcial del documento.** — RF-COM-04, RF-COM-11
  - Hecho cuando: un test comprueba que el mismo documento no se repite entre compras activas, salvo `SIN_DOCUMENTO`.

## Casos de uso

- [ ] **T5. Implementar `ComprasPort.tiene_compras()` de 0002d.** — RF-COM-02
  - Hecho cuando: un proveedor con compras no se puede eliminar (escenario de 0002d con el puerto real) y un proveedor desactivado no aparece en el selector de compras (RF-COM-03).

- [ ] **T6. Crear `RegistrarCompra` con la entrada de inventario.** — RF-COM-04, RF-COM-05, RF-COM-08 a RF-COM-10
  - Hecho cuando: "Compra con factura separa el IGV del costo", "Compra con boleta no separa IGV", "No se compran productos que se producen" y "Bonificación del proveedor con costo cero" están en verde.

- [ ] **T7. Agregar lotes y vencimientos a `RegistrarCompra`.** — RF-COM-06, RF-COM-07, RF-COM-19
  - Hecho cuando: "Compra de mercadería perecible ingresa con lote y vencimiento", "Mercadería con lote exige lote y vencimiento en la compra", "Un lote existente con el mismo vencimiento suma la cantidad" y "Un lote existente con otro vencimiento se rechaza" están en verde.

- [ ] **T8. Agregar las validaciones de documento y fecha.** — RF-COM-11, RF-COM-12, RF-COM-20
  - Hecho cuando: "Documento del proveedor duplicado", "Validaciones de la compra" y "Una factura exige un proveedor con RUC" están en verde.

- [ ] **T9. Garantizar la inmutabilidad de la compra registrada.** — RF-COM-13
  - Hecho cuando: un test comprueba que no existe ninguna operación de edición y que el detalle es de solo lectura.

## Pantallas

- [ ] **T10. Crear `/compras/nueva` con líneas dinámicas (HTMX) y totales en vivo.** — RF-COM-04 a RF-COM-12, RF-COM-19, RF-COM-20, RNF-COM-01
  - Hecho cuando: un test de vista registra una compra de 10 líneas; las columnas de lote solo aparecen para productos con lote.

- [ ] **T11. Crear el listado `/compras/` con filtros y el detalle con enlace al kardex.** — RF-COM-13, RF-COM-14
  - Hecho cuando: un test comprueba los filtros por proveedor, fecha, estado y número, y el enlace a los movimientos.

## Cierre

- [ ] **T12. Verificar la spec completa.** — RF-COM-04 a RF-COM-14, RF-COM-19, RF-COM-20
  - Hecho cuando: `pytest tests/purchasing tests/acceptance -k E04a` en verde; lint en verde; `MEMORY.md` actualizado.
