# Tareas 0007c — Facturación: notas de crédito y descargas

Estado: borrador (ejemplo). **No ejecutar:** `spec.md` y `plan.md` siguen en borrador (constitución, art. 2.1). Depende de la validación del contador (RF-FAC-25).

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Dominio puro

- [ ] **T1. Implementar `resolver_nc_en_espera(estado_original, hoy)`.** — RF-FAC-25, RF-FAC-26
  - Hecho cuando: un test comprueba: espera con el original pendiente, se envía con fecha del día al aceptarse, y `NO_REQUERIDA` si el original es rechazado.

- [ ] **T2. Replicar valor, ISC e IGV de cada línea del original en la NC total.** — RF-FAC-27
  - Hecho cuando: "La nota de crédito total replica el ISC del comprobante original" está en verde como test unitario.

## Casos de uso

- [ ] **T3. Emitir la NC con motivo `01`, `06` o `02` y su serie.** — RF-FAC-24
  - Hecho cuando: "Anular una venta con factura emite una nota de crédito" está en verde.

- [ ] **T4. Soportar la NC en espera y la no requerida.** — RF-FAC-25, RF-FAC-26, RF-FAC-28
  - Hecho cuando: "La NC espera a que el comprobante original sea aceptado" y "Sin NC si el comprobante original fue rechazado" están en verde, y la NC usa el mismo ciclo de reintentos.

- [ ] **T5. Crear las descargas de PDF, XML y CDR solo para la empresa dueña.** — RF-FAC-29, RNF-FAC-03
  - Hecho cuando: un test comprueba que otra empresa recibe 404 y que no hay enlaces públicos.

- [ ] **T6. Enviar el comprobante al cliente por email (automático y manual) vía outbox.** — RF-FAC-30
  - Hecho cuando: "Envío automático al cliente" está en verde y queda registrada la fecha de envío.

- [ ] **T7. Crear la bandeja con filtros y exportación CSV.** — RF-FAC-31
  - Hecho cuando: un test comprueba los filtros por fecha, tipo, serie, estado y cliente, y que el CSV coincide con la pantalla.

- [ ] **T8. Señalar las ventas con comprobante rechazado sin reemitir.** — RF-FAC-32
  - Hecho cuando: "Las ventas con comprobante rechazado sin reemitir quedan señaladas" está en verde.

## Cierre

- [ ] **T9. Verificar la spec completa.** — RF-FAC-24 a RF-FAC-32
  - Hecho cuando: `pytest tests/billing tests/acceptance -k E07c` en verde; lint en verde; `MEMORY.md` actualizado.
