# Tareas 0005a — Producción: recetas y órdenes de producción

Estado: borrador (ejemplo). **No ejecutar:** `spec.md` y `plan.md` siguen en borrador (constitución, art. 2.1). Depende de Q10 y Q12.

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Dominio puro

- [ ] **T1. Implementar la receta versionada y el escalado de insumos.** — RF-PRD-01, RF-PRD-02, RF-PRD-03, RF-PRD-05
  - Hecho cuando: `test_receta.py` comprueba que solo se admiten `INSUMO` activos, que editar una receta usada crea la versión 2 y que 1000 L escalan 100 kg a 200,0000 kg.

- [ ] **T2. Implementar la máquina de estados de la OP.** — RF-PRD-18, RF-PRD-33
  - Hecho cuando: `test_maquina_estados.py` prueba parametrizado todas las transiciones válidas e inválidas del diagrama.

- [ ] **T3. Implementar `litros_sugeridos()` por faltante de presentaciones.** — RF-PRD-07
  - Hecho cuando: `test_sugerencia.py` reproduce los 95,84 L del escenario de pedidos (spec 0006a).

- [ ] **T4. Implementar el costo por litro y el rendimiento del lote.** — RF-PRD-13, RF-PRD-14
  - Hecho cuando: un test reproduce el ejemplo de referencia: 798,00 / 409,5 L y rendimiento 104,00 %.

## Persistencia

- [ ] **T5. Crear los modelos de receta, versión, insumo de receta, OP, consumo y vínculo OP–pedido.** — RF-PRD-01, RF-PRD-04, RF-PRD-08
  - Hecho cuando: la migración se aplica y un test comprueba la numeración `OP-000001` y que una OP conserva su versión de receta.

## Casos de uso

- [ ] **T6. Crear el CRUD de recetas con versionado.** — RF-PRD-01 a RF-PRD-03
  - Hecho cuando: "Editar una receta usada crea una nueva versión" y "La receta solo admite insumos" están en verde.

- [ ] **T7. Crear `PlanificarOP` con advertencia de faltantes y pedidos vinculados.** — RF-PRD-04 a RF-PRD-07
  - Hecho cuando: "Planificar una OP escala los insumos y advierte faltantes" está en verde.

- [ ] **T8. Crear `IniciarOP`, con la salida de insumos y el paso de pedidos a `EN_PRODUCCION`.** — RF-PRD-08, RF-PRD-09, RF-PRD-11
  - Hecho cuando: "Iniciar OP consume los insumos reales al costo promedio" y "No se inicia una OP con insumos insuficientes" están en verde.

- [ ] **T9. Probar el doble inicio concurrente.** — RF-PRD-12
  - Hecho cuando: con `TransactionTestCase`, dos inicios simultáneos de la misma OP consumen los insumos una sola vez.

- [ ] **T10. Crear `RegistrarConsumoAdicional`.** — RF-PRD-10
  - Hecho cuando: "Consumo adicional durante el proceso (dry hopping)" está en verde y un insumo sin stock se rechaza.

- [ ] **T11. Crear `TerminarOP` con el lote de granel.** — RF-PRD-13, RF-PRD-14
  - Hecho cuando: "Terminar OP crea el lote de granel con su costo por litro" y "Rendimiento mayor al 100 % se permite con advertencia" están en verde.

- [ ] **T12. Soportar la OP terminada con 0 L (lote perdido).** — RF-PRD-15
  - Hecho cuando: "Lote perdido se termina con 0 litros" está en verde (escenario `@pendiente-q10`: se activa cuando se apruebe Q10).

- [ ] **T13. Crear `AnularOP`, con reversión de consumos y pedidos vía `PedidosPort`.** — RF-PRD-16 a RF-PRD-19
  - Hecho cuando: "Anular una OP en proceso revierte los consumos", "Transiciones de estado inválidas", "Rol producción no puede anular" y "Anular una OP devuelve a CONFIRMADO solo los pedidos que dependían de ella" están en verde.

## Pantallas

- [ ] **T14. Crear las pantallas de recetas y de OP para tablet.** — RF-PRD-01 a RF-PRD-14, RNF-PRD-02
  - Hecho cuando: un test de vista recorre planificar → iniciar → terminar; la plantilla usa el layout de tablet (pendiente del wireframe).

## Cierre

- [ ] **T15. Verificar la spec completa.** — RF-PRD-01 a RF-PRD-19
  - Hecho cuando: `pytest tests/production tests/acceptance -k E05a` en verde, salvo `@pendiente-q10`; lint en verde; `MEMORY.md` actualizado.
