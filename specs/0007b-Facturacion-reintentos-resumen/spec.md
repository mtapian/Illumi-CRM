# Spec 0007b — Facturación: reintentos y resumen diario

Estado: borrador

Épica E07 (Facturación electrónica), parte 2 de 3. Depende de: 0007a.

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

- H1: Como gerente, quiero que los comprobantes que fallan se reintenten solos y que me avisen de los que necesitan atención antes de vencer el plazo legal.

## Definiciones

- **Plazo legal de envío:** días máximos para enviar un comprobante a SUNAT desde su emisión (configurable con fecha de vigencia; valor a confirmar con el contador).

- **Tipos, series y estados del comprobante:** ver spec 0007a.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-FAC-03 Reintentar comprobantes pendientes

- RF-FAC-15: MIENTRAS la facturación esté habilitada y haya comprobantes en `PENDIENTE` o `ERROR`, EL SISTEMA los reintenta cada 15 minutos durante los primeros 10 intentos y luego cada hora, hasta enviarlos o hasta que venza el plazo legal, siempre con **el mismo correlativo y la misma fecha de emisión** (RN-FAC-04, RN-FAC-08). Los reintentos siguen aunque la empresa esté suspendida o vencida, porque el envío es una obligación legal.
- RF-FAC-16: CUANDO reintenta, EL SISTEMA consulta primero el estado en el PSE; si SUNAT ya lo aceptó, lo marca `ACEPTADO` sin reenviarlo.
- RF-FAC-17: SI dos reintentos coinciden en el mismo comprobante, ENTONCES EL SISTEMA lo envía una sola vez.
- RF-FAC-18: CUANDO un comprobante llega a 10 intentos fallidos, EL SISTEMA lo marca "Requiere atención" en la bandeja y en el dashboard, sin dejar de reintentarlo.
- RF-FAC-19: MIENTRAS a un comprobante no enviado le queden 2 días o menos del plazo legal, EL SISTEMA lo muestra con la alerta "vence el plazo de envío en N días".
- RF-FAC-20: CUANDO un usuario con `facturacion.comprobante.gestionar` reintenta desde la bandeja (uno o varios), EL SISTEMA aplica las mismas reglas que el reintento automático.
- RF-FAC-21: SI un comprobante está `RECHAZADO`, ENTONCES EL SISTEMA no lo reintenta y lo marca "Requiere atención" hasta que se reemita con un correlativo nuevo para la misma venta. No se puede reemitir el comprobante de una venta anulada.

### UC-FAC-04 Enviar resumen diario de boletas (condicional a Q1)

- RF-FAC-22: MIENTRAS el PSE elegido exija que el emisor envíe el resumen diario, EL SISTEMA envía las boletas y las NC de boletas **solo** dentro del resumen de cada madrugada (del día anterior), registra el ticket y lo consulta hasta obtener respuesta; con respuesta aceptada, las marca `ACEPTADO`. Las facturas y sus NC se envían una por una.
- RF-FAC-23: SI el envío del resumen falla, ENTONCES EL SISTEMA lo reintenta.

## Requisitos no funcionales

- RNF-FAC-02: ≥ 99 % de los comprobantes del piloto aceptados dentro de las 24 h (PRD §8).

## Casos límite

- **Respuesta tardía del PSE:** el reintento consulta antes de reenviar y no duplica.

## Fuera de alcance

Firma directa con SUNAT, guía de remisión, notas de débito, NC parciales (por línea o descuento), motivos del catálogo 09 distintos de 01, 02 y 06, comunicación de baja, detracciones y percepciones, facturación en dólares, exportación.

## Criterios de finalización

- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- [NECESITA ACLARACIÓN] **PRD Q1:** ¿qué PSE/OSE? Define si UC-FAC-04 entra al MVP y quién genera el PDF.
- [NECESITA ACLARACIÓN] **Contador (PRD Q12):** plazo legal de envío a SUNAT, plazo de conservación de XML/CDR y si un comprobante rechazado se reemite con correlativo nuevo.
