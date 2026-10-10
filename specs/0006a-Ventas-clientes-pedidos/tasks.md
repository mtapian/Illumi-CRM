# Tareas 0006a — Ventas: clientes y pedidos

Estado: borrador (ejemplo). **No ejecutar:** `spec.md` y `plan.md` siguen en borrador (constitución, art. 2.1).

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Dominio puro

- [ ] **T1. Implementar la validación del documento del cliente (DNI, RUC, CE).** — RF-VEN-01, RF-VEN-02
  - Hecho cuando: "Validación del documento del cliente" está en verde como test unitario y de aceptación.

- [ ] **T2. Implementar `transicion_pedido(estado, evento)` con la tabla de transiciones.** — RF-VEN-16
  - Hecho cuando: `test_pedido.py` prueba parametrizado cada fila de la tabla y rechaza cualquier otra transición.

- [ ] **T3. Implementar `atrasado(fecha_entrega, estado, hoy)` y el faltante por línea.** — RF-VEN-08, RF-VEN-15
  - Hecho cuando: un test comprueba que un pedido `ENTREGADO` o `CANCELADO` nunca está atrasado y que el faltante cuenta solo stock sin vencer de todos los almacenes.

## Persistencia

- [ ] **T4. Crear los modelos de cliente, pedido, línea de pedido y vínculo con OP.** — RF-VEN-01, RF-VEN-06, RF-VEN-42
  - Hecho cuando: la migración se aplica y un test comprueba la numeración `P-000001` y que un pedido puede vincularse a varias OP.

- [ ] **T5. Crear el sembrador del cliente "Clientes varios" y registrarlo en 0001a.** — RF-VEN-03
  - Hecho cuando: después de registrar una empresa existe el cliente genérico.

## Casos de uso

- [ ] **T6. Crear el CRUD de clientes y su ficha.** — RF-VEN-01, RF-VEN-02, RF-VEN-04, RF-VEN-05
  - Hecho cuando: un test comprueba la ficha con pedidos, ventas, total de 90 días y última compra, y que un cliente con documentos no se elimina.

- [ ] **T7. Crear `CrearPedido` y la edición libre en `BORRADOR`.** — RF-VEN-06, RF-VEN-07
  - Hecho cuando: un test crea un pedido con precios precargados desde el precio de lista y lo edita en `BORRADOR`.

- [ ] **T8. Crear `ConfirmarPedido` con faltantes y propuesta de producción o compra.** — RF-VEN-08 a RF-VEN-11
  - Hecho cuando: "Confirmar pedido muestra faltantes y propone producir", "Pedido confirmado no se edita" y "Faltante de mercadería se compra, no se produce" están en verde.

- [ ] **T9. Implementar `PedidosPort` para producción (pasar a `EN_PRODUCCION`, `LISTO` o de vuelta a `CONFIRMADO`).** — RF-VEN-12, RF-VEN-13, RF-VEN-41, RF-VEN-42
  - Hecho cuando: "El pedido avanza con la producción vinculada", "Envasado que no cubre el pedido completo" y "Pedido en producción sin OP activa y sin stock suficiente vuelve a CONFIRMADO" están en verde.

- [ ] **T10. Permitir marcar `LISTO` manualmente si el stock cubre el pedido.** — RF-VEN-13
  - Hecho cuando: un test comprueba que se acepta con stock suficiente y se rechaza sin él.

- [ ] **T11. Crear `CancelarPedido`, que desvincula las OP sin anularlas.** — RF-VEN-37
  - Hecho cuando: "Cancelar pedido en producción desvincula la OP" y "Un pedido entregado no se cancela" están en verde.

## Pantallas

- [ ] **T12. Crear el tablero de pedidos por estado con atrasos.** — RF-VEN-15
  - Hecho cuando: "Alerta de pedidos atrasados" está en verde (pendiente del wireframe del tablero).

- [ ] **T13. Crear las pantallas de clientes y del pedido con líneas dinámicas (HTMX).** — RF-VEN-01, RF-VEN-06 a RF-VEN-11
  - Hecho cuando: un test de vista crea, edita y confirma un pedido de 3 líneas.

- [ ] **T14. Crear la API `GET /api/v1/pedidos`.** — RF-VEN-06, (RF-TEN-48)
  - Hecho cuando: un test con token devuelve solo los pedidos de la empresa, paginados.

## Cierre

- [ ] **T15. Verificar la spec completa.** — RF-VEN-01 a RF-VEN-16, RF-VEN-37, RF-VEN-41, RF-VEN-42
  - Hecho cuando: `pytest tests/sales tests/acceptance -k E06a` en verde; lint en verde; `MEMORY.md` actualizado.
