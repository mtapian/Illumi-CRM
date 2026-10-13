# Tareas 0002e — Catálogo: impuestos

Estado: aprobado (PO, 2026-10-11) · todas las tareas hechas (2026-10-12).

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8): una tarea a la vez, test primero, y `ruff check`, `ruff format --check`, `lint-imports` y `makemigrations --check` en verde.

- [x] **T1. Dominio: `validar_impuesto`, `validar_tasa`, `validar_impuestos` y `desglose_linea`.** — RF-CAT-53, 54, 57 a 59
  - Hecho cuando: `test_impuestos.py` cubre gravado, exonerado e inafecto con y sin ISC, el ISC de compra rechazado, y el ejemplo de 0006b cuadra.
- [x] **T2. Modelos de impuesto, tasa y producto–impuesto con sus constraints y el trigger de solo inserción.** — RF-CAT-53, 54, 56
  - Hecho cuando: un test comprueba nombre único por tipo, ISC solo de venta, tasa por fecha única, importe ≥ 0 y que una tasa no se edita ni se borra.
- [x] **T3. Casos de uso del maestro y sembrador de los seis impuestos iniciales.** — RF-CAT-52 a 55
  - Hecho cuando: una empresa nueva tiene "IGV 18%", "Exonerado" e "Inafecto" de venta y de compra, y los escenarios del maestro están en verde.
  - Nota: los escenarios de UC-CAT-10 llevan `@borrador` hasta T4 y T5; se quita al implementarlos.
- [x] **T9. Enmienda 1, dominio y modelo: criterio del impuesto y desglose general.** — RF-CAT-53, 54, 59
  - Hecho cuando: `desglose_linea` cubre fijo y % en la afectación y en el ISC (ejemplo de la spec: 100.00 → 67.80 + 16.95 + 15.25, y el de 0006b sigue igual); migración `criterio` con los valores por defecto; tests en verde.
- [x] **T10. Enmienda 1, maestro: criterio en `GuardarImpuesto` y en la pantalla.** — RF-CAT-53
  - Hecho cuando: el criterio se elige al crear, queda fijo con uso, la tasa se muestra en % o S/ según el criterio y el escenario del ISC porcentual está en verde.
  - Nota: el escenario del ISC porcentual necesita productos con impuestos; sigue con `@borrador` hasta T4 (el cálculo ya lo cubre `test_impuestos.py`).
- [x] **T4. Impuestos del producto en `CrearProducto` / `EditarProducto`, y fachada `impuestos_de_venta` / `igv_de_compra`.** — RF-CAT-56 a 59
  - Hecho cuando: los escenarios de exonerado, ISC por presentación, listas inválidas e ISC en servicio están en verde, y `isc_de_linea` da lo mismo que hoy para la cerveza.
- [x] **T5. Compras: IGV por línea con el impuesto de compra del producto.** — RF-CAT-61
  - Hecho cuando: el escenario del insumo exonerado con factura está en verde y los escenarios de 0004a y 0004b siguen en verde.
- [x] **T6. Conversión de datos (IGV de la empresa e ISC por producto).** — RF-CAT-60
  - Hecho cuando: `test_conversion.py` pasa con datos reales, es reversible y la empresa demo conserva sus tasas.
  - Hecho (2026-10-12): migración `0012_conversion_impuestos` (reversible): IGV efectivo de cada empresa (propio o de la plataforma) en los dos "IGV 18%"; ISC por litro → "ISC <litros> L" de monto fijo, compartido por historial; "IGV 18%" en cada casilla marcada; tolera empresas ya sembradas y productos con impuestos. Se retiran `ProductoIscTasa`, `isc_sistema`, `isc_codigo_tipo_sistema`, `AgregarTasaIsc` y los campos del ISC de la ficha; los litros quedan informativos. Escenarios de 0002a y 0002c ajustados a lo mínimo (el resto en T8). Compras mantiene el IGV de la empresa solo para un producto sin impuesto de compra.
- [x] **T7. Pantallas: maestro de impuestos y etiquetas en la ficha; IGV fuera de la configuración de la empresa.** — RF-CAT-53, 56; 0001a RF-TEN-15, 16
  - Hecho cuando: los tests de pantalla y la prueba de aislamiento pasan, y la configuración de la empresa ya no edita el IGV.
  - Hecho (2026-10-12): maestro `/catalogo/impuestos/`, etiquetas en la ficha (venta en Ventas; compra en Compras o en General si no hay esa pestaña) e IGV fuera de la configuración de la empresa. Los campos del ISC por litro siguen en la ficha hasta la conversión (T6).
- [x] **T8. Ajustar 0001a, 0002a, 0002c y 0004a (specs y escenarios) y verificar.** — todos
  - Hecho cuando: suite, lint, contratos y migraciones en verde; cada RF con escenario o test; `MEMORY.md` actualizado.
  - Hecho (2026-10-12): RF-TEN-15 y 16, RF-CAT-30, RF-CAT-23 y 27, RF-COM-08 ajustados; RF-CAT-26, 45, 46 y 48 marcados como reemplazados. Los RF de 0002e, todos cubiertos; RF-CAT-23 a 25 los cubre el escenario "Un cambio de tasa aplica desde su fecha".
