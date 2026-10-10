# Tareas 0008a — Finanzas: gastos operativos

Estado: borrador (ejemplo). **No ejecutar:** `spec.md` y `plan.md` siguen en borrador (constitución, art. 2.1). Depende de Q12.

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Dominio puro

- [ ] **T1. Implementar `gasto_del_periodo(doc_tipo, base, igv)`.** — RF-FIN-01
  - Hecho cuando: "El gasto del período excluye el IGV solo con factura" está en verde como test unitario, incluido el recibo por honorarios.

- [ ] **T2. Validar la fecha y el importe del gasto.** — RF-FIN-02
  - Hecho cuando: "Gasto con fecha futura" está en verde y un importe 0 se rechaza.

## Persistencia

- [ ] **T3. Crear los modelos de categoría de gasto y gasto.** — RF-FIN-01, RF-FIN-03
  - Hecho cuando: la migración se aplica y un test comprueba los campos de anulación (`anulado_en`, motivo).

- [ ] **T4. Crear el sembrador de categorías de gasto y registrarlo en 0001a.** — RF-FIN-03
  - Hecho cuando: después de registrar una empresa existen Planilla, Alquiler, Servicios, Marketing, Transporte y distribución, Mantenimiento y Otros.

## Casos de uso

- [ ] **T5. Crear `RegistrarGasto` con la advertencia de categorías de planta.** — RF-FIN-01, RF-FIN-04
  - Hecho cuando: "Advertencia por posible doble conteo con el costo indirecto de la OP" está en verde.

- [ ] **T6. Crear `AnularGasto`, que resta en el período de la anulación.** — RF-FIN-05
  - Hecho cuando: "Anular un gasto" y "Un gasto anulado en otro mes resta en el mes de la anulación" están en verde.

## Pantalla

- [ ] **T7. Crear la pantalla de gastos con filtros y el CRUD de categorías.** — RF-FIN-01, RF-FIN-03
  - Hecho cuando: un test de vista registra un gasto con factura y muestra la base y el IGV por separado.

## Cierre

- [ ] **T8. Verificar la spec completa.** — RF-FIN-01 a RF-FIN-05
  - Hecho cuando: `pytest tests/finance tests/acceptance -k E08a` en verde; lint en verde; `MEMORY.md` actualizado.
