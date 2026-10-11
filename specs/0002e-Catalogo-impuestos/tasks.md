# Tareas 0002e — Catálogo: impuestos

Estado: borrador (2026-10-10), pendiente de aprobación del PO y de la validación del contador (spec, dudas abiertas).

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8): una tarea a la vez, test primero, y `ruff check`, `ruff format --check`, `lint-imports` y `makemigrations --check` en verde.

- [ ] **T1. Dominio: `validar_impuesto`, `validar_tasa`, `validar_impuestos_de_venta`, `desglose_linea` y `sistema_isc`.** — RF-CAT-53, 54, 57 a 59
  - Hecho cuando: `test_impuestos.py` cubre gravado, exonerado e inafecto con ISC fijo, porcentual y sin ISC, y el ejemplo de 0006b cuadra.
- [ ] **T2. Modelos de impuesto, tasa y producto–impuesto con sus constraints y el trigger de solo inserción.** — RF-CAT-53, 54, 56
  - Hecho cuando: un test comprueba nombre único, tasa por fecha única, importe ≥ 0 y que una tasa no se edita ni se borra.
- [ ] **T3. Casos de uso del maestro y sembrador de los impuestos iniciales.** — RF-CAT-52 a 55
  - Hecho cuando: una empresa nueva tiene "IGV 18%", "Exonerado" e "Inafecto", y los escenarios del maestro están en verde.
- [ ] **T4. Impuestos del producto en `CrearProducto` / `EditarProducto`, y fachada `impuestos_de_venta`.** — RF-CAT-56 a 59
  - Hecho cuando: los escenarios de exonerado, ISC por presentación e ISC en servicio están en verde, y `isc_de_linea` da lo mismo que hoy para la cerveza.
- [ ] **T5. Conversión de datos (IGV de la empresa e ISC por producto).** — RF-CAT-60
  - Hecho cuando: `test_conversion.py` pasa con datos reales, es reversible y la empresa demo conserva sus tasas.
- [ ] **T6. Pantallas: maestro de impuestos y etiquetas en la ficha; IGV fuera de la configuración de la empresa.** — RF-CAT-53, 56; 0001a RF-TEN-15, 16
  - Hecho cuando: los tests de pantalla y la prueba de aislamiento pasan, y la configuración de la empresa ya no edita el IGV.
- [ ] **T7. Ajustar 0001a, 0002a, 0002c (specs y escenarios) y verificar.** — todos
  - Hecho cuando: suite, lint, contratos y migraciones en verde; cada RF con escenario o test; `MEMORY.md` actualizado.
