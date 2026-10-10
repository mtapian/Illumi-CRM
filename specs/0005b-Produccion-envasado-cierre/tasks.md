# Tareas 0005b — Producción: envasado, cierre y costo del lote

Estado: borrador (ejemplo). **No ejecutar:** `spec.md` y `plan.md` siguen en borrador (constitución, art. 2.1). Depende de Q12 y de los wireframes de envasado.

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Dominio puro

- [ ] **T1. Implementar `calcular_envasado()` con el ejemplo de referencia.** — RF-PRD-20, RF-PRD-24
  - Hecho cuando: `test_envasado.py` obtiene 1,893080 por botella y 43,500000 por barril, y el control 2023,58 = 819,00 + 1204,58.

- [ ] **T2. Probar la conservación del costo con hypothesis.** — RF-PRD-24
  - Hecho cuando: `test_conservacion.py` comprueba que Σ entradas = granel + materiales al céntimo con 3 o más presentaciones.

- [ ] **T3. Implementar las validaciones del envasado.** — RF-PRD-21, RF-PRD-22
  - Hecho cuando: un test comprueba que se rechazan un envasado que excede el granel y una presentación de otro granel.

## Persistencia

- [ ] **T4. Crear los modelos de envasado y línea de envasado.** — RF-PRD-20, RF-PRD-29
  - Hecho cuando: la migración se aplica y un test comprueba la numeración `E-000001` y varios envasados por OP.

## Casos de uso

- [ ] **T5. Crear `RegistrarEnvasado`: salida de granel y materiales, entrada de terminados.** — RF-PRD-20, RF-PRD-23, RF-PRD-24
  - Hecho cuando: "Envasado multipresentación con merma absorbida en el costo", "Conservación del costo en el envasado" y "Materiales insuficientes" están en verde.

- [ ] **T6. Agregar las validaciones y el lote existente.** — RF-PRD-21, RF-PRD-22, RF-PRD-25, RF-PRD-29
  - Hecho cuando: "Envasado que excede el granel disponible del lote", "Solo presentaciones del mismo granel" y "Segundo envasado del mismo lote en otra fecha" están en verde.

- [ ] **T7. Soportar el descarte (0 unidades) y el cierre automático.** — RF-PRD-26, RF-PRD-30
  - Hecho cuando: "La OP se cierra automáticamente al agotar el granel" está en verde y la merma aparece en "Mermas y ajustes".

- [ ] **T8. Probar dos envasados simultáneos del mismo lote.** — RF-PRD-28
  - Hecho cuando: con `TransactionTestCase`, el segundo se valida contra el saldo real.

- [ ] **T9. Crear `CerrarOP` manual con merma.** — RF-PRD-31
  - Hecho cuando: "Cierre manual con saldo registra merma" está en verde.

- [ ] **T10. Actualizar los pedidos vinculados al envasar y al cerrar, vía `PedidosPort`.** — RF-PRD-27, RF-PRD-32
  - Hecho cuando: "El pedido avanza con la producción vinculada" (spec 0006a) está en verde con un `PedidosPort` falso; el real llega con 0006a.

## Pantallas y reporte

- [ ] **T11. Crear la pantalla de envasado para tablet.** — RF-PRD-20, RNF-PRD-01, RNF-PRD-02
  - Hecho cuando: un test de vista registra un envasado de 3 presentaciones; la captura tiene un solo formulario.

- [ ] **T12. Crear el reporte de costo y rendimiento de la OP.** — RF-PRD-34
  - Hecho cuando: "Reporte de costo y rendimiento del lote" está en verde.

## Cierre

- [ ] **T13. Verificar la spec completa.** — RF-PRD-20 a RF-PRD-34
  - Hecho cuando: `pytest tests/production tests/acceptance -k E05b` en verde; el ejemplo de referencia se reproduce exacto; lint en verde; `MEMORY.md` actualizado.
