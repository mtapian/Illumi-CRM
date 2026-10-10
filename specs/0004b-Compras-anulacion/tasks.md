# Tareas 0004b — Compras: anulación

Estado: borrador (ejemplo). **No ejecutar:** `spec.md` y `plan.md` siguen en borrador (constitución, art. 2.1). Depende de Q12.

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Caso de uso

- [ ] **T1. Crear `AnularCompra` con `select_for_update` y la reversión de inventario.** — RF-COM-15, RF-COM-18
  - Hecho cuando: "Anular compra revierte el stock al mismo costo y recalcula el promedio" está en verde y el documento puede registrarse de nuevo.

- [ ] **T2. Rechazar la anulación de una compra ya consumida.** — RF-COM-16
  - Hecho cuando: "No se anula una compra cuyo stock ya se consumió" está en verde con el mensaje que indica el producto.

- [ ] **T3. Probar la doble anulación concurrente.** — RF-COM-17
  - Hecho cuando: "Doble anulación concurrente revierte una sola vez" está en verde con `TransactionTestCase`.

- [ ] **T4. Exigir `compras.compra.anular`.** — RF-COM-15
  - Hecho cuando: "Rol almacén no puede anular" está en verde.

## Pantalla

- [ ] **T5. Agregar el botón "Anular" con motivo al detalle de la compra.** — RF-COM-15, RF-COM-16
  - Hecho cuando: un test de vista anula con motivo y muestra el mensaje de rechazo con el producto consumido.

## Cierre

- [ ] **T6. Verificar la spec completa.** — RF-COM-15 a RF-COM-18
  - Hecho cuando: `pytest tests/purchasing tests/acceptance -k E04b` en verde; lint en verde; `MEMORY.md` actualizado.
