# Tareas 0008b — Finanzas: estado de resultados, dashboard y exportación

Estado: borrador (ejemplo). **No ejecutar:** `spec.md` y `plan.md` siguen en borrador (constitución, art. 2.1). Depende de Q10.

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Dominio puro

- [ ] **T1. Implementar `mes_actual(hoy)` y `margen()` sin dividir por cero.** — RF-FIN-06, RF-FIN-13
  - Hecho cuando: "Período sin ventas" está en verde como test unitario: los márgenes salen "—".

## SQL

- [ ] **T2. Crear la función `fn_estado_resultados` con ventas netas y costo de ventas.** — RF-FIN-06 a RF-FIN-08
  - Hecho cuando: un test de integración reproduce ventas 1400,00 y costo 560,00 del escenario del mes, con la anulación en el período en que se anula.

- [ ] **T3. Agregar mermas y ajustes, sin saldo inicial ni transferencias.** — RF-FIN-09
  - Hecho cuando: la línea "Mermas y ajustes" da 86,67 en el escenario del mes.

- [ ] **T4. Agregar pérdidas de producción, gastos y entregas gratuitas.** — RF-FIN-06, RF-FIN-10
  - Hecho cuando: "Entrega gratuita va a gastos de venta, no a ventas ni a costo de ventas" está en verde y los gastos suman 500,00.

- [ ] **T5. Crear las vistas de detalle por línea.** — RF-FIN-11
  - Hecho cuando: "Detalle de una línea" está en verde y la suma del detalle es igual a la línea.

- [ ] **T6. Crear la consulta de pendientes tributarios.** — RF-FIN-12
  - Hecho cuando: "Pendientes tributarios listados aparte" está en verde.

## Casos de uso y pantallas

- [ ] **T7. Crear la pantalla del estado de resultados con comparación de períodos.** — RF-FIN-06, RF-FIN-07
  - Hecho cuando: "Estado de resultados del mes" y "La anulación resta en el período en que se anula" están en verde.

- [ ] **T8. Mostrar la línea de pérdidas de producción.** — RF-FIN-06
  - Hecho cuando: "Pérdida de producción en el período" está en verde (escenario `@pendiente-q10`).

- [ ] **T9. Crear el dashboard con avisos cargados por permiso.** — RF-FIN-14
  - Hecho cuando: "El dashboard respeta los permisos" está en verde y las ventas se muestran sin IGV ni ISC.

- [ ] **T10. Crear la exportación CSV común (UTF-8 con BOM).** — RF-FIN-15, RF-FIN-16, RNF-FIN-01
  - Hecho cuando: "Exportación CSV compatible con Excel" y "Exportación sin permiso de costos" están en verde, con las mismas cifras que la pantalla.

- [ ] **T11. Crear la API del estado de resultados.** — RF-FIN-06, RNF-FIN-01, (RF-TEN-48)
  - Hecho cuando: un test con token devuelve las mismas cifras que la pantalla.

- [ ] **T12. Medir el rendimiento y el aislamiento del estado de resultados.** — RNF-FIN-02, RNF-FIN-03
  - Hecho cuando: un test comprueba p95 < 800 ms con el volumen del PRD y que la función nunca incluye datos de otra empresa.

## Cierre

- [ ] **T13. Verificar la spec completa.** — RF-FIN-06 a RF-FIN-16
  - Hecho cuando: `pytest tests/finance tests/acceptance -k E08b` en verde, salvo `@pendiente-q10`; lint en verde; `MEMORY.md` actualizado.
