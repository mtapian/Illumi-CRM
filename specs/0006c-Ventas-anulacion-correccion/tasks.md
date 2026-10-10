# Tareas 0006c — Ventas: anulación y corrección de cliente

Estado: borrador (ejemplo). **No ejecutar:** `spec.md` y `plan.md` siguen en borrador (constitución, art. 2.1). Depende de la validación del contador (RF-VEN-32).

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Casos de uso

- [ ] **T1. Crear `AnularVenta` con NC registrada en la misma operación.** — RF-VEN-32
  - Hecho cuando: un test comprueba que la venta pasa a `ANULADA` de inmediato y que la NC queda registrada con motivo `01` o `06`.

- [ ] **T2. Reingresar la mercadería a los mismos lotes y al costo original.** — RF-VEN-33
  - Hecho cuando: "Anular venta revierte stock a los mismos lotes y costo" está en verde.

- [ ] **T3. Anular sin reingreso, manteniendo el costo de ventas.** — RF-VEN-34
  - Hecho cuando: "Anular sin reingreso de mercadería mantiene el costo de ventas" está en verde.

- [ ] **T4. Devolver el pedido a `LISTO` o `CONFIRMADO` según el reingreso.** — RF-VEN-35
  - Hecho cuando: "Anular venta de un pedido devuelve el pedido a LISTO" está en verde y sin reingreso vuelve a `CONFIRMADO`.

- [ ] **T5. Probar la doble anulación concurrente y el permiso.** — RF-VEN-32, RF-VEN-36
  - Hecho cuando: "Doble anulación concurrente revierte una sola vez" y "Rol ventas no puede anular" están en verde.

- [ ] **T6. Crear `CorregirClienteVenta` (NC `02` + comprobante nuevo, sin mover stock).** — RF-VEN-39
  - Hecho cuando: "Corregir el RUC de una factura no mueve stock ni costo" está en verde.

- [ ] **T7. Rechazar la corrección si el original no fue aceptado.** — RF-VEN-40
  - Hecho cuando: "No se corrige el cliente si el comprobante aún no fue aceptado" está en verde.

## Pantalla

- [ ] **T8. Agregar "Anular" (con motivo y casilla de reingreso) y "Corregir cliente" al detalle de la venta.** — RF-VEN-32, RF-VEN-33, RF-VEN-39
  - Hecho cuando: un test de vista anula con y sin reingreso y corrige el cliente de una factura aceptada.

## Cierre

- [ ] **T9. Verificar la spec completa.** — RF-VEN-32 a RF-VEN-36, RF-VEN-39, RF-VEN-40
  - Hecho cuando: `pytest tests/sales tests/acceptance -k E06c` en verde; lint en verde; `MEMORY.md` actualizado.
