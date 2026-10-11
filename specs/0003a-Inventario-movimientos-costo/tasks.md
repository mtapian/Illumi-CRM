# Tareas 0003a — Inventario: almacenes, movimientos y costo promedio

Estado: implementado (2026-10-10). T1 y T2 se hicieron antes, por orden del PO.

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Dominio puro

- [x] **T1. Implementar `CostoProducto` con `entrada()`.** — RF-INV-18
  - Hecho cuando: `test_costo.py` reproduce las dos primeras filas del ejemplo de la spec: 100 × 4,00 y +50 × 5,00 ⇒ 150 KG, 650,00, 4,333333.

- [x] **T2. Implementar `salida_al_promedio()`, incluida la salida que vacía.** — RF-INV-24
  - Hecho cuando: un test comprueba que −30 sale por 130,00 sin cambiar el promedio y que la salida que deja 0 sale por el valor restante y deja 0,00.

- [x] **T3. Implementar `reversion_de_entrada()`.** — RF-INV-20
  - Hecho cuando: un test anula la compra de 50 KG a 5,00 con saldo 150/650,00 y obtiene 100 KG, 400,00 y promedio 4,000000.

- [x] **T4. Implementar `salir()` sobre la existencia por almacén y lote.** — RF-INV-19
  - Hecho cuando: un test comprueba que una salida mayor al stock del almacén y lote lanza `StockInsuficiente`.

- [x] **T5. Implementar `lote_vencido`, `orden_fefo` y `asignar_fefo` con `hoy`.** — RF-INV-22
  - Hecho cuando: un test comprueba que el lote que vence hoy se puede usar, el vencido no, y que los lotes sin vencimiento y el stock sin lote salen al final.

- [x] **T6. Implementar `validar_salida_de_lote()` y `hubo_salidas_posteriores()`.** — RF-INV-21, RF-INV-23
  - Hecho cuando: un test comprueba que un lote vencido solo sale por `MERMA` y que una salida en otro almacén cuenta como posterior.

- [x] **T6b. Implementar `validar_bien()`, `sugerir_vencimiento()` y `validar_lote_existente()`.** — RF-INV-25, RF-INV-26
  - Hecho cuando: `test_lotes.py` comprueba que un servicio se rechaza, que el vencimiento sugerido es ingreso + vida útil y que un lote existente con otro vencimiento se rechaza.

- [x] **T7. Implementar `inversos_de()`.** — RF-INV-20
  - Hecho cuando: un test comprueba que los inversos usan el costo original de cada movimiento.

## Persistencia

- [x] **T8. Crear los modelos de almacén, lote, stock y costo de producto, con sus constraints.** — RF-INV-19, RF-INV-24
  - Hecho cuando: un test comprueba `CHECK cantidad >= 0`, `CHECK valor_total >= 0` y la unicidad de stock por producto, almacén y lote.

- [x] **T9. Crear el modelo de movimiento con el trigger de inmutabilidad y `UNIQUE(revierte_id)`.** — RF-INV-17, RF-INV-20
  - Hecho cuando: "El kardex es inmutable" está en verde y una segunda reversión del mismo movimiento falla en la base de datos.

- [x] **T10. Crear el sembrador del almacén "Principal" y registrarlo en 0001a.** — RF-INV-01
  - Hecho cuando: después de registrar una empresa existe el almacén "Principal".

## Servicio de inventario

- [x] **T11. Crear `InventarioService.registrar_entrada()` con el orden de locks del plan 000.** — RF-INV-17, RF-INV-18
  - Hecho cuando: "Entrada con stock en cero toma el costo de la entrada" está en verde y cada entrada genera un solo movimiento con su saldo.

- [x] **T12. Crear `InventarioService.registrar_salida()` con FEFO.** — RF-INV-17, RF-INV-19, RF-INV-22 a RF-INV-24
  - Hecho cuando: "Asignación FEFO excluye lotes vencidos", "Stock disponible insuficiente sin contar vencidos", "Lote vencido solo sale por merma", "Lote vencido no sale por corrección" y "Una salida no puede dejar stock negativo" están en verde.

- [x] **T13. Probar la concurrencia sobre el último stock.** — RF-INV-19
  - Hecho cuando: "Concurrencia sobre el último stock" está en verde con `TransactionTestCase`.

- [x] **T14. Crear `InventarioService.revertir()`.** — RF-INV-20, RF-INV-21
  - Hecho cuando: un test de caso de uso revierte una entrada sin consumo y rechaza con `AnulacionConConsumoPosterior` una con salidas posteriores.

- [x] **T15. Comprobar la secuencia completa de costo del ejemplo.** — RF-INV-17, RF-INV-18, RNF-INV-01, RNF-INV-03
  - Hecho cuando: "Secuencia de entradas y salidas recalcula el promedio" está en verde.

## Almacenes

- [x] **T16. Crear el CRUD de almacenes y su desactivación.** — RF-INV-02, RF-INV-03
  - Hecho cuando: "Almacén con stock no se desactiva" está en verde y un nombre repetido en la empresa se rechaza.

## Cierre

- [x] **T17. Verificar la spec completa.** — RF-INV-01 a RF-INV-03, RF-INV-17 a RF-INV-24
  - Hecho cuando: `pytest tests/inventory tests/acceptance -k E03a` en verde; prueba de reconciliación en verde; lint en verde; `MEMORY.md` actualizado.
