# Spec 0007c — Facturación: notas de crédito y descargas

Estado: borrador

Épica E07 (Facturación electrónica), parte 3 de 3. Depende de: 0007a, 0007b, 0006c.

## Contexto y objetivo

En Perú, toda venta requiere un comprobante electrónico válido ante SUNAT. La cervecera necesita emitirlo desde la misma venta, sin pasos manuales, y anularlo correctamente si la venta se anula.

**Objetivo:** que cada venta tenga su comprobante aceptado por SUNAT (≥ 99 % dentro de las 24 h), sin que una caída de SUNAT o del PSE detenga la operación.

**Principios:**
- La venta no depende de SUNAT: si el PSE o SUNAT no responden, la venta queda registrada y el comprobante queda pendiente para reintento.
- En el MVP hay un solo canal de emisión: un PSE/OSE con API. El sistema no firma comprobantes por sí mismo.
- Las reglas tributarias que pueden cambiar (umbral de boleta, ISC, códigos, plazos) se configuran; no se fijan en el sistema.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Administrador | Configura la facturación (`facturacion.config.gestionar`) |
| Gerente | Gestiona la bandeja: reintenta, reemite, envía por email (`facturacion.comprobante.gestionar`) |
| Ventas | Ve y descarga comprobantes (`facturacion.comprobante.ver`) |
| Contador | Recibe los comprobantes y las alertas de plazo (fuera del sistema) |

## Historias de usuario

- H1: Como gerente, quiero que al anular una venta se emita la nota de crédito correcta.
- H2: Como vendedor, quiero descargar el PDF, el XML y el CDR, y enviarlos al cliente por email.

## Definiciones

- **Tipos, series, estados del comprobante e ISC:** ver spec 0007a. **Plazo legal de envío:** ver spec 0007b.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-FAC-05 Emitir nota de crédito

- RF-FAC-24: CUANDO se anula una venta (motivo `01` o `06`) o se corrige su cliente (motivo `02`, épica 0006 UC-VEN-08), EL SISTEMA registra una NC por el total con ese motivo del catálogo 09, la serie de NC que corresponde y la referencia al comprobante original.
- RF-FAC-25: MIENTRAS el comprobante original no esté `ACEPTADO` u `OBSERVADO`, EL SISTEMA deja la NC en `ESPERANDO_ORIGINAL` sin enviarla; cuando el original es aceptado, la envía con fecha de emisión del día del envío, de modo que el plazo legal corre desde que se puede enviar. *Regla pendiente de validación del contador (constitución, art. 5.5).*
- RF-FAC-26: SI el comprobante original termina `RECHAZADO`, ENTONCES EL SISTEMA marca la NC `NO_REQUERIDA`.
- RF-FAC-27: CUANDO se emite una NC por el total, EL SISTEMA replica el valor, el ISC y el IGV de cada línea del original (RN-FAC-10).
- RF-FAC-28: EL SISTEMA aplica a las NC el mismo ciclo de estados, reintentos y alertas de plazo.

### UC-FAC-06 Descargar y enviar comprobante

- RF-FAC-29: CUANDO un usuario con `facturacion.comprobante.ver` lo pide desde la venta o la bandeja, EL SISTEMA descarga el PDF, el XML o el CDR, solo si el comprobante es de su empresa.
- RF-FAC-30: CUANDO un comprobante queda `ACEPTADO` y el envío automático está activo y el cliente tiene email, EL SISTEMA le envía el PDF y el XML y registra la fecha de envío. También se puede enviar manualmente.
- RF-FAC-31: EL SISTEMA ofrece una bandeja de comprobantes con filtros por fecha, tipo, serie, estado y cliente, exportable a CSV.
- RF-FAC-32: EL SISTEMA muestra en la bandeja y en el dashboard las ventas cuyo comprobante está `RECHAZADO` y todavía no se reemitió.

## Requisitos no funcionales

- RNF-FAC-03: Las descargas solo se sirven a usuarios de la empresa dueña del comprobante; nunca por un enlace público.

## Casos límite

- **Venta anulada antes de que su comprobante llegue a SUNAT:** la venta queda anulada; la NC espera en `ESPERANDO_ORIGINAL` y la bandeja muestra el par. El estado de resultados lista estas ventas aparte (épica 0008).

## Fuera de alcance

Firma directa con SUNAT, guía de remisión, notas de débito, NC parciales (por línea o descuento), motivos del catálogo 09 distintos de 01, 02 y 06, comunicación de baja, detracciones y percepciones, facturación en dólares, exportación.

## Criterios de finalización

- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- [NECESITA ACLARACIÓN] **Contador (PRD Q12):** plazo legal de envío a SUNAT, plazo de conservación de XML/CDR y si un comprobante rechazado se reemite con correlativo nuevo.
