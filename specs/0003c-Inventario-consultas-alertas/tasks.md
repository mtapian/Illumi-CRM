# Tareas 0003c — Inventario: stock, kardex y alertas

Estado: borrador (ejemplo). **No ejecutar:** `spec.md` y `plan.md` siguen en borrador (constitución, art. 2.1).

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Dominio puro

- [ ] **T1. Implementar `lotes_por_vencer()` y `bajo_minimo()`.** — RF-INV-14, RF-INV-15
  - Hecho cuando: un test comprueba el límite de 30 días (incluido) y que el stock igual al mínimo cuenta como bajo.

## Consultas

- [ ] **T2. Crear las vistas SQL `vw_stock_valorizado` y `vw_kardex`.** — RF-INV-04, RF-INV-06
  - Hecho cuando: un test de integración comprueba que la vista de stock suma por almacén y lote y que el kardex muestra el saldo de cada movimiento.

- [ ] **T3. Crear `ConsultarStock` con filtros.** — RF-INV-04, RF-INV-05
  - Hecho cuando: "Stock valorizado por tipo" está en verde y los filtros por tipo, almacén, familia, stock bajo y con stock devuelven lo esperado.

- [ ] **T4. Crear `ConsultarKardex` con filtros y exportación CSV.** — RF-INV-06, RF-INV-07
  - Hecho cuando: "Reconciliación del kardex con el stock" está en verde y el CSV tiene las mismas filas que la pantalla.

- [ ] **T5. Crear `ProductosBajoMinimo` y `LotesPorVencer` para el dashboard.** — RF-INV-14 a RF-INV-16
  - Hecho cuando: "Alerta de lotes por vencer" y "Alerta de stock bajo mínimo" están en verde y los lotes vencidos se marcan en rojo.

## Pantallas

- [ ] **T6. Crear las pantallas de stock y kardex, con costos ocultos sin `inventario.costo.ver`.** — RF-INV-04, RF-INV-06, (RF-TEN-51)
  - Hecho cuando: un test de vista comprueba que un usuario sin `inventario.costo.ver` no ve costo promedio ni valorización ("Ocultar costos a un rol" de 0001c en verde).

- [ ] **T7. Crear la API `GET /api/v1/stock`.** — RF-INV-04, (RF-TEN-48)
  - Hecho cuando: un test con token devuelve solo el stock de la empresa, paginado.

- [ ] **T8. Medir el rendimiento con 100 000 movimientos.** — RNF-INV-02
  - Hecho cuando: `test_rendimiento.py` comprueba p95 < 800 ms en stock y kardex.

## Cierre

- [ ] **T9. Verificar la spec completa.** — RF-INV-04 a RF-INV-07, RF-INV-14 a RF-INV-16
  - Hecho cuando: `pytest tests/inventory tests/acceptance -k E03c` en verde; lint en verde; `MEMORY.md` actualizado.
