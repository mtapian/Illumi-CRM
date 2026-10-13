# Tareas 0006a — Ventas: clientes y pedidos

Estado: aprobado (PO: "go", 2026-10-13) · **todas las tareas hechas (2026-10-13)**.

Una tarea a la vez: test primero (en rojo), código, test en verde, marcar y parar (art. 8.1).

- [x] **T1. Reglas de documento genéricas.** — RF-VEN-02, 49
  - `ReglasDocumento` y `validar_numero` en `shared/domain/documentos.py` (especial `RUC`).
  - Hecho cuando: `test_documentos.py` cubre DNI, CE, RUC, pasaporte y sin documento con sus mensajes.
- [x] **T2. Maestro de tipos de documento (plataforma).** — RF-VEN-49
  - Modelo, migración con los cinco tipos, `GuardarTipoDocumento`, fachada y pantalla `/plataforma/tipos-documento/`.
  - Hecho cuando: sus tests de caso de uso y de pantalla pasan (abreviatura y código fijos; desactivar).
- [x] **T3. Proveedores con el maestro.** — 0002d RF-COM-01
  - El proveedor valida con las reglas del maestro y ofrece los tipos activos.
  - Hecho cuando: los tests y escenarios de 0002d, 0004a y 0004b siguen en verde.
- [x] **T4. App `sales`, modelos y migraciones; "Clientes varios".** — RF-VEN-01, 03, 05, 06, 11
  - Tablas de §2 con sus CHECK y el trigger de líneas; sembrador del genérico y migración para las empresas existentes; import-linter.
  - Hecho cuando: un test prueba cada constraint y el trigger, y una empresa nueva y una existente tienen "Clientes varios".
- [x] **T5. Clientes: casos de uso (CRU) y búsqueda.** — RF-VEN-01, 02, 05, 44, 50
  - `GuardarCliente`, `CambiarEstadoCliente` y la búsqueda por nombre o documento; sin eliminar.
  - Hecho cuando: `test_clientes.py` cubre documento único, genérico siempre activo, búsqueda y permisos.
- [x] **T6. Pedido: dominio y casos de uso.** — RF-VEN-06 a 08, 11, 14, 16, 37, 48
  - Estados, líneas, total; `CrearPedido`, `EditarPedido`, `AprobarPedido`, `CancelarPedido`.
  - Hecho cuando: `test_pedido.py` y `test_pedidos.py` cubren transiciones, aprobar exige stock (todos los faltantes), líneas fijas al aprobar, cancelar con motivo y permisos.
- [x] **T7. Disponibilidad e indicadores.** — RF-VEN-15, 45, 46
  - `InventarioService.disponibles`; faltante, quiebre, listo y atrasado.
  - Hecho cuando: los tests cubren stock vencido, servicios, varios almacenes y dos pedidos que comparten stock.
- [x] **T8. Pantallas de clientes.** — RF-VEN-01 a 05, 43, 44
  - `/ventas/clientes/` con grilla, formulario y ficha con pedidos; menú "Ventas".
  - Hecho cuando: el test de pantalla y la prueba de aislamiento pasan.
- [x] **T9. Pantallas de pedidos y alerta del inicio.** — RF-VEN-06 a 08, 11, 15, 37, 45 a 48, 50
  - Lista y Kanban con filtros, alta y ficha con disponibilidad, selector de cliente con búsqueda y registro al vuelo, acciones; alerta "pedidos con quiebre de stock".
  - Hecho cuando: el test de pantalla y la prueba de aislamiento pasan.
- [x] **T10. Escenarios de aceptación y cierre.** — todos
  - `tests/acceptance/pasos_ventas.py` y `test_e06a.py`; spec, plan y tareas a "implementada"; `MEMORY.md`.
  - Hecho cuando: los escenarios de 0006a están en verde; suite, lint, formato, contratos y migraciones en verde; cada RF con escenario o test.
