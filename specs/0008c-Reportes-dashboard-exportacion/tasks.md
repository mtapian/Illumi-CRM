# Tareas 0008c — Reportes: dashboard, exportación e indicadores de los listados

Estado: aprobado (PO: "go", 2026-10-13).

Una tarea a la vez: test primero (en rojo), código, test en verde, marcar y parar (art. 8.1).

- [x] **T1. Gráficos SVG.** — RF-FIN-18 a 21, 24
  - `shared/interfaces/graficos.py`: línea, dona y barras.
  - Hecho cuando: los tests unitarios cubren escalas, etiquetas con valores y el caso sin datos.
- [x] **T2. Exportación XLSX y CSV.** — RF-FIN-15, 25
  - `shared/interfaces/exportar.py`.
  - Hecho cuando: el XLSX generado se vuelve a leer con sus columnas y filas, el CSV lleva BOM, y el tope rechaza con su mensaje.
- [x] **T3. Consultas de ventas para el inicio.** — RF-FIN-14, 18 a 23
  - `sales/infrastructure/reportes.py`.
  - Hecho cuando: cada consulta da lo esperado con cancelados, pagos anulados, sin categoría y la hora de Lima.
- [x] **T4. Inicio: tarjetas y barra de avisos.** — RF-FIN-14, 17
  - Registro `tablero`, vista y plantilla del inicio; tarjetas de ventas, productos y clientes.
  - Hecho cuando: el test de pantalla ve cada tarjeta solo con su permiso y la barra solo con avisos.
- [x] **T5. Inicio: gráficos y tablas.** — RF-FIN-18 a 24
  - Paneles de ventas 14 días, por mes, cobrado por método, por categoría, más vendidos y últimas ventas.
  - Hecho cuando: el test de pantalla ve los cuatro gráficos y las dos tablas, y el de rendimiento pasa.
- [x] **T6. Exportar productos y kardex.** — RF-FIN-15, 16
  - Columnas compartidas con la grilla; el kardex conserva su CSV y suma XLSX.
  - Hecho cuando: los tests exportan con filtros y sin costos.
- [x] **T7. Exportar pedidos (por SKU) y cobranzas.** — RF-FIN-15, 16, 25
  - Hecho cuando: los tests exportan una fila por línea con los filtros y el tope.
- [x] **T8. Indicadores por estado en pedidos y cobranzas.** — RF-FIN-26
  - Hecho cuando: el test ve los conteos (y saldos en cobranzas) con los filtros salvo el estado, y la tarjeta filtra.
- [ ] **T9. Escenarios de aceptación y cierre.** — todos
  - `tests/acceptance/pasos_reportes.py` y `test_e08c.py`; se quita `@borrador`; spec, plan y tareas a "implementada"; `MEMORY.md`; Docker.
  - Hecho cuando: los 8 escenarios en verde; suite, lint, formato, contratos y migraciones en verde; cada RF con escenario o test.
