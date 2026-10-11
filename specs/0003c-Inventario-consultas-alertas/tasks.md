# Tareas 0003c — Inventario: stock, kardex y alertas

Estado: implementado (2026-10-10).

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8): una tarea a la vez, test primero, y `ruff check`, `ruff format --check`, `lint-imports` y `makemigrations --check` en verde.

- [x] **T1. Dominio: `por_vencer`, `dias_restantes` y `bajo_minimo`.** — RF-INV-14, RF-INV-15
  - Hecho cuando: `test_alertas.py` cubre el día del vencimiento, el último día de la ventana, mínimo 0 y stock igual al mínimo.
- [x] **T2. `ConfigInventario`, índices y pantalla de configuración.** — RF-INV-15, RNF-INV-02
  - Hecho cuando: sin fila valen 30 días; 0 y 366 se rechazan; la migración crea los índices.
- [x] **T3. Consulta y pantalla de stock con detalle, filtros y valorización por categoría.** — RF-INV-04, RF-INV-05, RF-INV-16
  - Hecho cuando: "Stock valorizado por categoría" está en verde y sin `inventario.costo.ver` no aparecen costos ni valor.
- [x] **T4. Consulta y pantalla de kardex con filtros, cursor, enlace al ajuste y CSV.** — RF-INV-06, RF-INV-07
  - Hecho cuando: "Reconciliación del kardex con el stock" está en verde, el CSV respeta filtros y costos, y sin producto no hay saldos.
- [x] **T5. Registro de avisos y avisos "Stock bajo" y "Por vencer" en el dashboard; filtro "stock bajo" del catálogo con `≤`.** — RF-INV-14, RF-INV-15, RF-INV-16, RF-INV-30
  - Hecho cuando: "Alerta de lotes por vencer" y "Alerta de stock bajo mínimo" están en verde y quien no tiene `inventario.stock.ver` no ve los avisos.
- [x] **T6. Rendimiento con 100 000 movimientos.** — RNF-INV-02
  - Hecho cuando: el listado de stock y el kardex de un producto responden con p95 < 800 ms en el test.
- [x] **T7. Verificar la spec completa.** — RF-INV-04 a RF-INV-07, RF-INV-14 a RF-INV-16, RF-INV-30
  - Hecho cuando: suite, lint, contratos y migraciones en verde; cada RF con escenario o test; `MEMORY.md` actualizado.
