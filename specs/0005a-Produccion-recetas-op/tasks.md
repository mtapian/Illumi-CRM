# Tareas 0005a — Producción: órdenes de producción

Estado: aprobado (PO: "dale", 2026-10-12) · **todas las tareas hechas (2026-10-12)**.

Una tarea a la vez: test primero (en rojo), código, test en verde, marcar y parar (art. 8.1).

- [x] **T1. Dominio de la OP.** — RF-PRD-14, 15, 33, 37, 38, 41, 42, 44, 46, 47
  - `production/domain/op.py` y `errores.py` (§3); app `production` registrada y en import-linter (capas, dominio puro, contrato como el de compras).
  - Hecho cuando: `tests/production/unit/test_op.py` pasa con el ejemplo de la spec (1.880080 por botella; lote IPA-0020 sugerido) y los contratos siguen en verde.
- [x] **T2. Modelos y migración.** — RF-PRD-15, 16, 36, 41
  - `OrdenProduccion` y `OpComponente` con los CHECK de §2 y el trigger de componentes inmutables tras Finalizada o Anulada.
  - Hecho cuando: un test de integración prueba cada CHECK y el trigger, y `makemigrations --check` está limpio.
- [x] **T3. Inventario para producción.** — RF-PRD-09, 39, 41, 46
  - `InventarioService.existencias_en_orden` y `consumido`; las salidas guardan `fecha=hoy`.
  - Hecho cuando: sus tests pasan (orden FEFO o FIFO sin vencidos, importes y lotes de las salidas, fecha de la salida) y 0003a–0004b siguen en verde.
- [x] **T4. Crear, editar, pasar a en proceso y anular.** — RF-PRD-16, 18, 33, 35 a 38, 44, 45
  - `CrearOp`, `EditarOp`, `PasarAEnProceso`, `AnularOp`; correlativo `OP-000001`; responsable; contador de OP en curso (RF-TEN-32).
  - Hecho cuando: `test_ordenes.py` cubre crear con y sin receta, editar sin stock, transiciones, anular sin stock y permisos.
- [x] **T5. Finalizar.** — RF-PRD-09, 14, 15, 41, 42, 46, 47
  - `FinalizarOp` según §4: faltantes de todos los componentes, salidas, entrada con lote (nuevo o heredado), servicios, costo indirecto, lote perdido.
  - Hecho cuando: `test_ordenes.py` reproduce las dos OP del ejemplo de la spec y el lote perdido (pérdida 790.00), y un faltante no deja movimientos.
- [x] **T6. Concurrencia y reconciliación.** — RF-PRD-12; art. 4.6
  - Dos finalizaciones simultáneas (dos hilos); OP encadenadas con semillas: el kardex reproduce stock y valor.
  - Hecho cuando: ambos tests pasan estables en 3 corridas.
- [x] **T7. Receta desde la OP.** — RF-PRD-38
  - `GuardarReceta` en el catálogo (`catalogo.producto.gestionar`, ciclos, historial).
  - Hecho cuando: su test pasa y la OP puede guardar sus componentes como receta del producto.
- [x] **T8. Pantallas.** — RF-PRD-34, 36 a 39, 41, 44 a 46, 48
  - `/produccion/`, `/produccion/nueva/`, `/produccion/<id>/` (componentes dinámicos, disponibilidad, diálogo de finalizar, Más acciones › Anular, pestaña Costos), menú "Producción", enlace desde el kardex.
  - Hecho cuando: `tests/production/integration/test_pantallas.py` y la prueba de aislamiento pasan.
- [x] **T9. Accesos.** — spec, Impacto
  - Se retiran `produccion.recetas` y `produccion.envasado` del catálogo de accesos y de las plantillas de rol; se revisan los escenarios de 0001b/0001c que los nombran.
  - Hecho cuando: la suite de 0001b y 0001c sigue en verde y `migrate` marca como obsoletos los permisos retirados (la sincronización de 0001b no borra: conserva el historial).
- [x] **T10. Escenarios de aceptación y cierre.** — todos
  - `tests/acceptance/pasos_produccion.py` y `test_e05a.py`; spec, plan y tareas a "implementada"; `MEMORY.md`.
  - Hecho cuando: los 14 escenarios de 0005a están en verde; suite, lint, formato, contratos y migraciones en verde; cada RF con escenario o test.

## Enmienda 1: varios productos de salida (implementada, 2026-10-12)

- [x] **T11. Dominio: reparto del costo por factor y lote por salida.** — RF-PRD-52
  - Hecho cuando: `repartir` reproduce el ejemplo (1.893080 y 43.500000), cuadra al céntimo y pasa a comunes lo asignado a una salida con 0.
- [x] **T12. Modelo y migración: `OpSalida`, componente asignado a una salida, conversión de las OP existentes.** — RF-PRD-49, 51
  - Hecho cuando: un test de conversión pasa una OP con un producto a una salida con sus componentes asignados, y es reversible.
- [x] **T13. Casos de uso: salidas al crear y editar, receta por salida, finalizar con producida y lote por salida.** — RF-PRD-49 a 52
  - Hecho cuando: el envasado en dos presentaciones del ejemplo da sus costos y lotes; los tests de 0005a siguen en verde.
- [x] **T14. Pantallas: productos de salida, columna "Para", diálogo de finalizar y Costos por salida.** — RF-PRD-53
  - Hecho cuando: el test de pantalla crea y finaliza una OP con dos salidas.
- [x] **T15. Escenario de aceptación y cierre.** — RF-PRD-49 a 53
  - Hecho cuando: el escenario del envasado en dos presentaciones está en verde; suite, lint, contratos y migraciones en verde; `MEMORY.md` actualizado.

