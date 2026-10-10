# Tareas 0007a — Facturación: configuración y emisión

Estado: borrador (ejemplo). **No ejecutar:** `spec.md` y `plan.md` siguen en borrador (constitución, art. 2.1). Depende de Q1, T1 y del código de tipo de sistema ISC.

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Dominio puro

- [ ] **T1. Implementar `modo_emision(estado_empresa, facturacion_habilitada)`.** — RF-FAC-04, RF-FAC-05
  - Hecho cuando: un test comprueba los tres modos: interno en trial sin facturación, pendiente sin enviar si está deshabilitada, y envío normal.

- [ ] **T2. Implementar la validación de series.** — RF-FAC-01, RF-FAC-06
  - Hecho cuando: "Validación de series" está en verde como test unitario.

- [ ] **T3. Armar el `ComprobanteDTO` con ISC (tributo `2000`) y entrega gratuita.** — RF-FAC-12, RF-FAC-13
  - Hecho cuando: un test reproduce 19,88 / 224,19 / 43,93 y la transferencia gratuita 500,00 / 251,00 / 135,18 con total cobrado 0.

## Persistencia

- [ ] **T4. Crear los modelos de configuración de facturación (credenciales cifradas), serie y comprobante.** — RF-FAC-01, RF-FAC-02, RF-FAC-07
  - Hecho cuando: un test comprueba que las credenciales no se leen en claro desde la base de datos ni aparecen en los logs.

- [ ] **T5. Crear el sembrador de series por defecto y registrarlo en 0001a.** — RF-FAC-01
  - Hecho cuando: después de registrar una empresa existen `F001`, `B001`, `FC01` y `BC01`.

- [ ] **T6. Crear el correlativo por serie sin huecos ni duplicados.** — RF-FAC-07
  - Hecho cuando: un test con 2 hilos obtiene correlativos consecutivos; si la venta se revierte, el correlativo no se consume.

## Puerto e infraestructura

- [ ] **T7. Crear el puerto `EmisorComprobantes` y un PSE simulado para tests.** — RF-FAC-08, RF-FAC-09
  - Hecho cuando: los tests de emisión corren contra el simulado, que puede aceptar, rechazar o no responder.

- [ ] **T8. Crear el almacenamiento de la copia propia de XML y CDR.** — RF-FAC-08, RNF-FAC-01
  - Hecho cuando: un test comprueba que XML y CDR quedan guardados y se pueden leer aunque el PSE no responda (backend definido por T1).

## Casos de uso

- [ ] **T9. Crear `ConfigurarFacturacion` y `ProbarConexion`.** — RF-FAC-01 a RF-FAC-03
  - Hecho cuando: "Probar conexión con el PSE" está en verde y la pantalla nunca muestra las credenciales completas.

- [ ] **T10. Emitir el comprobante en `on_commit` desde el outbox.** — RF-FAC-07, RF-FAC-08, RF-FAC-10, RF-FAC-11
  - Hecho cuando: "Venta con boleta emite el comprobante aceptado" y "El reintento usa el mismo correlativo" están en verde.

- [ ] **T11. Manejar la caída del PSE.** — RF-FAC-09
  - Hecho cuando: "Caída del PSE no impide la venta" está en verde.

- [ ] **T12. Soportar el comprobante interno y la facturación deshabilitada.** — RF-FAC-04, RF-FAC-05
  - Hecho cuando: "Facturación deshabilitada en trial emite un comprobante interno" y "Empresa activa sin facturación habilitada deja el comprobante pendiente" están en verde.

- [ ] **T13. Emitir comprobantes con ISC y entregas gratuitas.** — RF-FAC-12, RF-FAC-13
  - Hecho cuando: "Boleta de cerveza con ISC de sistema específico", "Producto con categoría de ISC sin tarifa vigente" y "Entrega gratuita como retiro de bienes con ISC e IGV" están en verde.

- [ ] **T14. Generar la representación impresa (A4 y ticket de 80 mm).** — RF-FAC-14
  - Hecho cuando: un test comprueba que el PDF tiene emisor, cliente, líneas, totales, importe en letras, QR y la leyenda.

## Cierre

- [ ] **T15. Verificar la spec completa.** — RF-FAC-01 a RF-FAC-14
  - Hecho cuando: `pytest tests/billing tests/acceptance -k E07a` en verde con el PSE simulado; lint en verde; `MEMORY.md` actualizado.
