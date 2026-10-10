# Tareas 0007b — Facturación: reintentos y resumen diario

Estado: borrador (ejemplo). **No ejecutar:** `spec.md` y `plan.md` siguen en borrador (constitución, art. 2.1). Depende de Q1 y Q12.

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Dominio puro

- [ ] **T1. Implementar `toca_reintentar(comprobante, ahora, plazo_dias)`.** — RF-FAC-15, RF-FAC-21
  - Hecho cuando: un test comprueba cada 15 minutos hasta el intento 10, luego cada hora, nunca un `RECHAZADO` y nunca después del plazo legal.

- [ ] **T2. Implementar `dias_para_plazo(fecha_emision, plazo_dias, hoy)`.** — RF-FAC-19
  - Hecho cuando: un test comprueba la alerta con 2 días o menos y el plazo leído con vigencia.

## Casos de uso

- [ ] **T3. Crear el comando de reintentos con `select_for_update(skip_locked)` y advisory lock.** — RF-FAC-15, RF-FAC-17
  - Hecho cuando: "Dos reintentos simultáneos envían el comprobante una sola vez" está en verde.

- [ ] **T4. Consultar el estado en el PSE antes de reenviar.** — RF-FAC-16
  - Hecho cuando: "Respuesta tardía del primer envío" está en verde.

- [ ] **T5. Marcar "Requiere atención" tras 10 intentos y en los rechazados.** — RF-FAC-18, RF-FAC-21
  - Hecho cuando: "Reintentos agotados requieren atención" y "Un comprobante rechazado no se reintenta" están en verde.

- [ ] **T6. Mostrar la alerta de plazo legal.** — RF-FAC-19
  - Hecho cuando: "Alerta por plazo legal de envío" está en verde.

- [ ] **T7. Crear el reintento manual desde la bandeja (uno o varios).** — RF-FAC-20
  - Hecho cuando: un test comprueba que el reintento manual aplica las mismas reglas que el automático.

- [ ] **T8. Crear el resumen diario de boletas y su consulta de ticket.** — RF-FAC-22, RF-FAC-23
  - Hecho cuando: "Resumen diario de boletas y sus NC" está en verde (escenario `@pendiente-q1`) y un envío fallido se reintenta.

## Métrica

- [ ] **T9. Medir la aceptación dentro de 24 h.** — RNF-FAC-02
  - Hecho cuando: un test comprueba que el reporte calcula el % de comprobantes aceptados dentro de 24 h desde la fecha de aceptación.

## Cierre

- [ ] **T10. Verificar la spec completa.** — RF-FAC-15 a RF-FAC-23
  - Hecho cuando: `pytest tests/billing tests/acceptance -k E07b` en verde, salvo `@pendiente-q1`; lint en verde; `MEMORY.md` actualizado.
