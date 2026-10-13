# Tareas 0006b — Ventas: facturación, entrega y cobranza

Estado: aprobado (PO: "ok", 2026-10-13).

Una tarea a la vez: test primero (en rojo), código, test en verde, marcar y parar (art. 8.1).

- [x] **T1. Dominio de facturación y cobranza.** — RF-VEN-19, 24, 25, 27, 28, 52 a 57
  - `sales/domain/facturacion.py` y `sales/domain/cobranza.py`.
  - Hecho cuando: los tests unitarios cubren cada regla con sus mensajes.
- [x] **T2. Modelos, migración y permisos.** — RF-VEN-58
  - Campos de facturación en `Pedido` y `PedidoLinea`, `Cobranza`, `Cuota`, `Pago`, `MetodoPago` con sus CHECK; trigger de líneas ajustado; métodos de pago sembrados (empresas nuevas y existentes); `ventas.cobranza.ver` y `.gestionar` en el catálogo de accesos, las plantillas y los roles existentes.
  - Hecho cuando: un test prueba cada constraint, el trigger y la siembra; migraciones reversibles.
- [x] **T3. Facturar y entregar.** — RF-VEN-17, 19 a 28, 38, 51
  - `FacturarPedido` y `EntregarPedido` con el repositorio.
  - Hecho cuando: los tests de caso de uso cubren desglose, costo congelado, lote elegido, estrategia, servicios, todos los faltantes, producto desactivado, comprobante, crédito en cuotas (solo factura, suma = total), que nada cambie si falla, y la concurrencia por el último stock.
- [x] **T4. Cobranzas y métodos de pago.** — RF-VEN-54 a 57, 59
  - `RegistrarPago`, `AnularPago`, `GuardarMetodoPago`, `CambiarEstadoMetodoPago`.
  - Hecho cuando: los tests cubren pago parcial y total, sobre el saldo, cobranza pagada, anular (vuelve a Pendiente, no dos veces), nombre duplicado, inactivo no se ofrece, permisos y dos pagos simultáneos.
- [x] **T5. Venta directa.** — RF-VEN-18, 29, 52
  - `VentaDirecta` (crear, facturar, pagos, entregar en una transacción; token).
  - Hecho cuando: los tests cubren la venta con dos pagos, pagos que no suman el total y el token repetido.
- [ ] **T6. Pantalla del pedido: facturar y entregar; ficha del cliente.** — RF-VEN-04, 17, 19, 20, 51
  - Diálogo "Facturar" con lotes, "Confirmar entrega", desglose y costo; resumen del cliente.
  - Hecho cuando: el test de pantalla pasa (costos ocultos sin permiso).
- [ ] **T7. Pantalla de venta directa.** — RF-VEN-18, 29, 52
  - Líneas y pagos dinámicos, búsqueda de cliente, token.
  - Hecho cuando: el test de pantalla pasa y un doble envío deja una sola venta.
- [ ] **T8. Pantallas de cobranzas y métodos de pago.** — RF-VEN-53 a 59
  - Listado y ficha de cobranza, registrar y anular pagos, maestro de métodos de pago, menú.
  - Hecho cuando: el test de pantalla y la prueba de aislamiento pasan.
- [ ] **T9. Escenarios de aceptación y cierre.** — todos
  - `tests/acceptance/pasos_ventas.py` y `test_e06b.py`; se quita `@borrador`; spec, plan y tareas a "implementada"; `MEMORY.md`; Docker.
  - Hecho cuando: los escenarios de 0006b y los de 0006a están en verde; suite, lint, formato, contratos y migraciones en verde; cada RF con escenario o test.
