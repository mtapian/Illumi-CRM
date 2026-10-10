# Tareas 0002b — Catálogo: presentaciones y materiales

Estado: borrador (ejemplo). **No ejecutar:** `spec.md` y `plan.md` siguen en borrador (constitución, art. 2.1).

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Dominio puro

- [ ] **T1. Implementar `validar_presentacion()`.** — RF-CAT-15, RF-CAT-16
  - Hecho cuando: `test_presentacion.py` rechaza contenido 0, granel inactivo, ningún material, un material que no es `ENVASE` y una cantidad 0; acepta 0,0417.

- [ ] **T2. Implementar `materiales_para(presentacion, unidades)`.** — RF-CAT-16, RNF-CAT-02
  - Hecho cuando: un test comprueba que 240 unidades piden 240 botellas y 10,0080 cajas (4 decimales).

## Persistencia y casos de uso

- [ ] **T3. Crear los modelos de presentación y material de presentación.** — RF-CAT-15, RF-CAT-16, RF-CAT-17
  - Hecho cuando: la migración se aplica y un test comprueba los `CHECK > 0` y `UNIQUE(presentacion_id, material_id)`.

- [ ] **T4. Crear `DefinirPresentacion`.** — RF-CAT-15 a RF-CAT-17
  - Hecho cuando: "Crear presentación en botella con materiales fraccionados", "Un granel con varias presentaciones", "Terminado sin materiales" y "Datos de presentación inválidos" están en verde.

- [ ] **T5. Permitir editar materiales y bloquear el contenido con movimientos.** — RF-CAT-18
  - Hecho cuando: "Cambiar materiales aplica solo a envasados futuros" está en verde y cambiar el contenido de una presentación con movimientos lanza `ContenidoInmutable`.

- [ ] **T6. Exponer `presentacion()` y `materiales_para()` en `CatalogoQuery`.** — RF-CAT-16
  - Hecho cuando: un test de la fachada devuelve los materiales de una presentación para N unidades; es lo que usará la spec 0005b.

## Pantalla

- [ ] **T7. Agregar el formset de materiales al formulario de `TERMINADO`.** — RF-CAT-15, RF-CAT-16
  - Hecho cuando: un test de vista guarda una presentación con 5 materiales y muestra el error junto al material inválido.

## Cierre

- [ ] **T8. Verificar la spec completa.** — RF-CAT-15 a RF-CAT-18
  - Hecho cuando: `pytest tests/catalog tests/acceptance -k E02b` en verde; lint en verde; cada RF con escenario o test; `MEMORY.md` actualizado.
