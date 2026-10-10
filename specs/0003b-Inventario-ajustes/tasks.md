# Tareas 0003b — Inventario: ajustes

Estado: borrador (ejemplo). **No ejecutar:** `spec.md` y `plan.md` siguen en borrador (constitución, art. 2.1). Depende de Q12 (sustento de mermas).

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Dominio puro

- [ ] **T1. Implementar `costo_de_entrada_ajuste()` con la tabla de costos por tipo.** — RF-INV-08, RF-INV-25
  - Hecho cuando: un test por tipo de ajuste comprueba el costo aplicado y que una entrada al promedio de un producto que nunca tuvo costo exige el costo unitario.

- [ ] **T2. Implementar `validar_saldo_inicial()` y `diferencia_conteo()`.** — RF-INV-09, RF-INV-11
  - Hecho cuando: un test comprueba que el saldo inicial exige costo > 0 y producto sin movimientos, y que un conteo igual al sistema da diferencia 0.

## Persistencia

- [ ] **T3. Crear los modelos de ajuste y línea de ajuste.** — RF-INV-08
  - Hecho cuando: la migración se aplica y un test comprueba la numeración correlativa por empresa.

## Casos de uso

- [ ] **T4. Crear `RegistrarAjuste` para `SALDO_INICIAL`, con creación del lote.** — RF-INV-08 a RF-INV-10
  - Hecho cuando: "Saldo inicial sin costo es rechazado", "Ajuste sin motivo es rechazado" y "Saldo inicial de producto con lote crea el lote" están en verde.

- [ ] **T5. Agregar `CONTEO`, `MERMA` y `CORRECCION` a `RegistrarAjuste`.** — RF-INV-08, RF-INV-11, RF-INV-25
  - Hecho cuando: "Ajuste por conteo físico calcula la diferencia" y "Conteo igual al sistema no mueve stock" están en verde.

- [ ] **T6. Agregar `TRANSFERENCIA` (salida y entrada juntas, al mismo costo).** — RF-INV-12
  - Hecho cuando: "Transferencia entre almacenes no cambia el costo ni el resultado" está en verde.

- [ ] **T7. Crear `AnularAjuste`.** — RF-INV-13
  - Hecho cuando: "Anular un ajuste revierte sus movimientos" está en verde, y anular una transferencia revierte la salida y la entrada.

## Pantalla

- [ ] **T8. Crear la pantalla de ajustes con líneas dinámicas (HTMX) y el reporte de diferencias de conteo.** — RF-INV-08, RF-INV-11
  - Hecho cuando: un test de vista registra un conteo de 3 líneas y el reporte del mes muestra la diferencia valorizada.

## Cierre

- [ ] **T9. Verificar la spec completa.** — RF-INV-08 a RF-INV-13, RF-INV-25
  - Hecho cuando: `pytest tests/inventory tests/acceptance -k E03b` en verde; lint en verde; `MEMORY.md` actualizado.
