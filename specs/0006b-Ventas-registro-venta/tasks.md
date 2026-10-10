# Tareas 0006b — Ventas: registro de la venta

Estado: borrador (ejemplo). **No ejecutar:** `spec.md` y `plan.md` siguen en borrador (constitución, art. 2.1). Depende de Q3.

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Dominio puro

- [ ] **T1. Implementar `desglose(total_linea, igv_pct, isc)` sin ISC.** — RF-VEN-22
  - Hecho cuando: `test_desglose.py` reproduce 288,00 = 244,07 + 43,93.

- [ ] **T2. Agregar el ISC de Sistema Específico al desglose.** — RF-VEN-22, RF-VEN-28
  - Hecho cuando: un test reproduce 19,88 / 224,19 / 43,93 y rechaza una línea pagada cuyo valor queda ≤ 0.

- [ ] **T3. Implementar `desglose_gratuito()` para entregas gratuitas.** — RF-VEN-30
  - Hecho cuando: un test reproduce 5 barriles: valor referencial 500,00, ISC 251,00, IGV 135,18 y total cobrado 0.

- [ ] **T4. Implementar `validar_credito()` y `validar_comprobante_cliente()`.** — RF-VEN-24, RF-VEN-25, RF-VEN-27
  - Hecho cuando: "Cuotas inválidas en una venta a crédito" y "Reglas del comprobante según el cliente" están en verde como tests unitarios; el umbral se lee con vigencia.

## Persistencia

- [ ] **T5. Crear los modelos de venta, línea comercial, reparto por lote y cuota, con la clave de idempotencia.** — RF-VEN-21, RF-VEN-27, RF-VEN-29
  - Hecho cuando: la migración se aplica y un test comprueba la numeración `V-000001` y `UNIQUE(idempotency_key)`.

## Casos de uso

- [ ] **T6. Crear `RegistrarVenta` directa con FEFO y costo congelado.** — RF-VEN-18 a RF-VEN-23, RF-VEN-38
  - Hecho cuando: "Venta directa con boleta, FEFO y snapshot de costo", "El costo histórico no cambia cuando cambia el costo promedio", "Selección manual de lote" y "Solo se venden presentaciones y mercadería activas" están en verde.

- [ ] **T7. Crear el comprobante `PENDIENTE` en la misma transacción (outbox).** — RF-VEN-21, RNF-VEN-01
  - Hecho cuando: un test comprueba que si el proceso falla después de guardar la venta, el comprobante existe; la emisión real llega con 0007a.

- [ ] **T8. Registrar la venta desde un pedido y pasarlo a `ENTREGADO`.** — RF-VEN-14, RF-VEN-17
  - Hecho cuando: "Venta desde pedido con factura a crédito en cuotas" está en verde.

- [ ] **T9. Validar stock sin vencidos y concurrencia.** — RF-VEN-26
  - Hecho cuando: "Stock insuficiente sin contar lotes vencidos" y "Dos ventas simultáneas por el último stock" están en verde.

- [ ] **T10. Garantizar la idempotencia del formulario.** — RF-VEN-29
  - Hecho cuando: "Doble envío no duplica la venta" está en verde.

- [ ] **T11. Soportar la venta mixta y la entrega gratuita.** — RF-VEN-22, RF-VEN-30
  - Hecho cuando: "Venta mixta de cerveza propia y mercadería de reventa" y "Entrega gratuita como retiro de bienes con ISC e IGV" (spec 0007a) están en verde.

## Pantallas

- [ ] **T12. Crear la pantalla de venta directa (mostrador).** — RF-VEN-18, RF-VEN-19, RNF-VEN-02
  - Hecho cuando: un test de vista registra una venta de 3 productos con búsqueda y vuelto; la pantalla cabe en una sola vista.

- [ ] **T13. Crear la impresión en A4 y ticket de 80 mm.** — RF-VEN-31
  - Hecho cuando: un test de vista genera ambos formatos con los datos del comprobante.

- [ ] **T14. Crear la API `GET /api/v1/ventas`.** — RF-VEN-17, (RF-TEN-48)
  - Hecho cuando: un test con token devuelve solo las ventas de la empresa, paginadas, sin costos si el usuario técnico no tiene `inventario.costo.ver`.

## Cierre

- [ ] **T15. Verificar la spec completa.** — RF-VEN-17 a RF-VEN-31, RF-VEN-38
  - Hecho cuando: `pytest tests/sales tests/acceptance -k E06b` en verde; lint en verde; `MEMORY.md` actualizado.
