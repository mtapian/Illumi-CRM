# Tareas 0003b — Inventario: ajustes

Estado: implementado (2026-10-10).

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Dominio puro

- [x] **T1. Implementar `costo_de_entrada_ajuste()` con la tabla de costos por tipo.** — RF-INV-08, RF-INV-27
  - Hecho cuando: un test por tipo de ajuste comprueba el costo aplicado y que una entrada al promedio de un producto que nunca tuvo costo exige el costo unitario.

- [x] **T2. Implementar `validar_saldo_inicial()`, `diferencia_conteo()` y `validar_ajuste()`.** — RF-INV-08, RF-INV-09, RF-INV-11, RF-INV-12
  - Hecho cuando: un test comprueba costo > 0 y producto sin movimientos en el saldo inicial, diferencia 0 en el conteo igual, motivo obligatorio y transferencia al mismo almacén rechazada.

- [x] **T3. Permitir `CONTEO` y `TRANSFERENCIA` en lotes vencidos; motivo `ANULACION` en los inversos.** — RF-INV-29, RF-INV-13
  - Hecho cuando: un test comprueba que un lote vencido sale por conteo y transferencia pero no por venta ni corrección, y los tests de 0003a siguen en verde.

## Persistencia

- [x] **T4. Crear los modelos de ajuste y línea de ajuste con sus constraints y el correlativo.** — RF-INV-08, RF-INV-28
  - Hecho cuando: la migración se aplica y un test comprueba la numeración correlativa por empresa, el motivo obligatorio y el destino solo en transferencias.

## Casos de uso

- [x] **T5. Crear `RegistrarAjuste` para `SALDO_INICIAL`, `MERMA` y `CORRECCION`, con lote opcional.** — RF-INV-08 a RF-INV-10, RF-INV-27
  - Hecho cuando: "Saldo inicial sin costo es rechazado", "Ajuste sin motivo es rechazado" y "Saldo inicial con lote crea el lote" están en verde.

- [x] **T6. Agregar `CONTEO` a `RegistrarAjuste`.** — RF-INV-11, RF-INV-27
  - Hecho cuando: "Ajuste por conteo físico calcula la diferencia" y "Conteo igual al sistema no mueve stock" están en verde.

- [x] **T7. Agregar `InventarioService.transferir()` y `TRANSFERENCIA`.** — RF-INV-12
  - Hecho cuando: "Transferencia entre almacenes no cambia el costo ni el resultado" está en verde (salvo el paso del estado de resultados, parcial hasta 0008b) y una transferencia que vacía el origen deja el promedio igual.

- [x] **T8. Crear `AnularAjuste`.** — RF-INV-13
  - Hecho cuando: "Anular un ajuste revierte sus movimientos" está en verde, anular una transferencia revierte salida y entrada sin cambiar el costo, y un ajuste anulado no se anula otra vez.

## Pantalla

- [x] **T9. Crear `/inventario/ajustes/` (nuevo y últimos) y `/inventario/ajustes/<id>/` (detalle y anular).** — RF-INV-08, RF-INV-11, RF-INV-13
  - Hecho cuando: un test de vista registra un conteo de 3 líneas, el detalle de otra empresa da 404 (ruta en la prueba de aislamiento) y sin `inventario.ajuste.anular` no aparece "Anular" y el servidor lo rechaza.

## Cierre

- [x] **T10. Verificar la spec completa.** — RF-INV-08 a RF-INV-13, RF-INV-27 a RF-INV-29
  - Hecho cuando: `pytest tests/inventory tests/acceptance -k E03b` en verde; lint, contratos y migraciones en verde; `MEMORY.md` actualizado.
