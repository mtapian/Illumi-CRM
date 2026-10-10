# Tareas 0002c — Catálogo: categorías y tarifas de ISC

Estado: aprobada (PO, 2026-10-10). Se ejecutan una spec a la vez, en orden de dependencia.

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Dominio puro

- [ ] **T1. Implementar `tarifa_aplicable(tarifas, fecha)`.** — RF-CAT-24, RF-CAT-25
  - Hecho cuando: `test_isc.py` comprueba la tarifa el día antes, el día de inicio y el día después de un cambio, y `None` antes de la primera tarifa.

- [ ] **T2. Implementar `isc_linea(cantidad, contenido_l, tarifa)`.** — RF-CAT-23, RF-CAT-25, RF-CAT-27
  - Hecho cuando: un test comprueba que 24 × 0,33 L × 2,51 = 19,88 y que sin categoría el ISC es 0.

## Persistencia

- [ ] **T3. Crear los modelos de categoría y tarifa de ISC, con el trigger de tarifas inmutables.** — RF-CAT-22 a RF-CAT-24
  - Hecho cuando: un test de integración comprueba que un `UPDATE` o `DELETE` sobre `catalog_isc_tarifa` falla y que `sistema` solo admite `ESPECIFICO`.

## Casos de uso

- [ ] **T4. Crear `CrearCategoriaIsc` con su primera tarifa y `AgregarTarifaIsc`.** — RF-CAT-22, RF-CAT-23, RF-CAT-24
  - Hecho cuando: "Tarifa de ISC configurable por empresa con vigencia" está en verde.

- [ ] **T5. Crear `DesactivarCategoriaIsc`.** — RF-CAT-28
  - Hecho cuando: un test comprueba que una categoría asignada a productos activos no se desactiva.

- [ ] **T6. Exigir el contenido en litros a los productos con categoría de ISC por litro.** — RF-CAT-26
  - Hecho cuando: "Mercadería con ISC requiere contenido en litros" está en verde.

- [ ] **T7. Exponer `isc_aplicable(producto, fecha)` en `CatalogoQuery`.** — RF-CAT-25, RF-CAT-27
  - Hecho cuando: "Producto sin categoría de ISC no paga ISC" está en verde y una categoría sin tarifa vigente lanza `IscSinTarifaVigente`.

## Pantalla

- [ ] **T8. Crear `/catalogo/isc/` con el historial de tarifas y la acción "Agregar tarifa".** — RF-CAT-22, RF-CAT-24, RF-CAT-28
  - Hecho cuando: un test de vista comprueba que solo `catalogo.isc.gestionar` accede y que no hay botones para editar ni borrar tarifas.

## Cierre

- [ ] **T9. Verificar la spec completa.** — RF-CAT-22 a RF-CAT-28
  - Hecho cuando: `pytest tests/catalog tests/acceptance -k E02c` en verde; lint en verde; cada RF con escenario o test; `MEMORY.md` actualizado.
