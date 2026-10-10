# Spec 007 — Facturación electrónica (SUNAT)

Estado: borrador

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

- H1: Como administrador, quiero configurar el PSE, las credenciales y las series una sola vez para que los comprobantes salgan solos.
- H2: Como vendedor, quiero que cada venta emita su boleta o factura sin pasos adicionales.
- H3: Como gerente, quiero que los comprobantes que fallan se reintenten solos y que me avisen de los que necesitan atención antes de vencer el plazo legal.
- H4: Como gerente, quiero que al anular una venta se emita la nota de crédito correcta.
- H5: Como vendedor, quiero descargar el PDF, el XML y el CDR, y enviarlos al cliente por email.

## Definiciones

- **Tipos de comprobante:** factura (`01`), boleta (`03`), nota de crédito (`07`) y comprobante interno (solo pruebas; rotulado "NO ES COMPROBANTE DE PAGO").
- **Series por defecto:** factura `F001`, boleta `B001`, NC de factura `FC01`, NC de boleta `BC01`. Cuatro caracteres alfanuméricos; las de factura y su NC empiezan con `F`, las de boleta y su NC con `B`.
- **Estados del comprobante:** `PENDIENTE` → `ACEPTADO` | `OBSERVADO` (aceptado con observaciones) | `RECHAZADO` | `ERROR` (falla de comunicación). Las NC tienen además `ESPERANDO_ORIGINAL` y `NO_REQUERIDA`.
- **Plazo legal de envío:** días máximos para enviar un comprobante a SUNAT desde su emisión (configurable con fecha de vigencia; valor a confirmar con el contador).
- **ISC de la cerveza** (PRD Q2, respondido por el contador): Sistema Específico, **S/ 2.51 por litro desde el 2024-07-01**, sin importar el precio ni la graduación. Se configura por empresa en categorías de ISC con tarifas por vigencia (spec 002, UC-CAT-05). Base del IGV = valor + ISC; IGV = (valor + ISC) × 18 %; total = valor + ISC + IGV. En el comprobante: tributo `2000` y el código de tipo de sistema de la categoría.
- **Entrega gratuita:** retiro de bienes gravado con ISC e IGV sobre el valor referencial; va como transferencia gratuita y los impuestos los asume la empresa.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-FAC-01 Configurar facturación

- RF-FAC-01: CUANDO un usuario con `facturacion.config.gestionar` guarda la configuración (emisión sí/no, entorno `beta`/`produccion`, PSE y credenciales, datos del emisor, series, envío automático por email), EL SISTEMA la guarda si las series cumplen el formato (RN-FAC-05).
- RF-FAC-02: EL SISTEMA nunca muestra las credenciales completas, ni en pantalla, ni en registros, ni en la API (RN-FAC-06).
- RF-FAC-03: CUANDO el usuario pulsa "Probar conexión", EL SISTEMA prueba las credenciales con el PSE y guarda la fecha, el resultado y el mensaje.
- RF-FAC-04: MIENTRAS la empresa esté en prueba (`trial`) y la facturación esté deshabilitada, EL SISTEMA emite un comprobante interno rotulado "NO ES COMPROBANTE DE PAGO" y no llama al PSE.
- RF-FAC-05: MIENTRAS la facturación esté deshabilitada y la empresa no esté en prueba, EL SISTEMA crea el comprobante electrónico `PENDIENTE` pero no lo envía; al habilitar la facturación, lo envía con su fecha de emisión original.
- RF-FAC-06: CUANDO cambian las series, EL SISTEMA empieza la serie nueva en el correlativo 1; los comprobantes ya creados, incluidos los pendientes, conservan su serie y su correlativo.

### UC-FAC-02 Emitir comprobante

- RF-FAC-07: CUANDO se registra una venta (spec 006), EL SISTEMA crea su comprobante `PENDIENTE` con un correlativo por serie sin huecos ni duplicados, aunque el proceso se caiga justo después de guardar la venta (RN-FAC-02).
- RF-FAC-08: CUANDO el comprobante se envía al PSE, EL SISTEMA guarda el estado de la respuesta, el código, el mensaje, el hash, el PDF y **una copia propia** del XML y del CDR (RN-FAC-09).
- RF-FAC-09: SI el PSE o SUNAT no responden, ENTONCES EL SISTEMA deja el comprobante en `ERROR`, cuenta el intento y la venta sigue registrada.
- RF-FAC-10: CUANDO un comprobante queda `ACEPTADO`, EL SISTEMA registra la fecha y hora de aceptación (para la métrica de 24 h del PRD §8) y no permite modificarlo; solo se corrige con una NC (RN-FAC-03).
- RF-FAC-11: EL SISTEMA exige cliente con RUC en una factura; en una boleta aplica la regla de identificación de la spec 006 (RN-FAC-01).
- RF-FAC-12: CUANDO una línea tiene ISC, EL SISTEMA lo informa con el tributo `2000`, el código de tipo de sistema de su categoría y la base del IGV = valor + ISC (RN-FAC-07).
- RF-FAC-13: CUANDO una línea es una entrega gratuita, EL SISTEMA la informa como transferencia gratuita con su valor referencial, ISC e IGV, y total cobrado 0 (RN-FAC-11).
- RF-FAC-14: EL SISTEMA genera la representación impresa en A4 y en ticket de 80 mm, con datos del emisor y del cliente, líneas, totales, importe en letras, hash o código QR y la leyenda de representación impresa.

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

### UC-FAC-05 Emitir nota de crédito

- RF-FAC-24: CUANDO se anula una venta (motivo `01` o `06`) o se corrige su cliente (motivo `02`, spec 006 UC-VEN-08), EL SISTEMA registra una NC por el total con ese motivo del catálogo 09, la serie de NC que corresponde y la referencia al comprobante original.
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

- RNF-FAC-01: XML y CDR se conservan durante el plazo legal (configurable con fecha de vigencia; por defecto 5 años) en un almacenamiento con respaldo, sin opción de borrado.
- RNF-FAC-02: ≥ 99 % de los comprobantes del piloto aceptados dentro de las 24 h (PRD §8).
- RNF-FAC-03: Las descargas solo se sirven a usuarios de la empresa dueña del comprobante; nunca por un enlace público.

## Casos límite

- **Venta anulada antes de que su comprobante llegue a SUNAT:** la venta queda anulada; la NC espera en `ESPERANDO_ORIGINAL` y la bandeja muestra el par. El estado de resultados lista estas ventas aparte (spec 008).
- **Respuesta tardía del PSE:** el reintento consulta antes de reenviar y no duplica.
- **Tarifa de ISC sin vigencia** a la fecha de emisión: la venta se rechaza (spec 002).

## Fuera de alcance

Firma directa con SUNAT, guía de remisión, notas de débito, NC parciales (por línea o descuento), motivos del catálogo 09 distintos de 01, 02 y 06, comunicación de baja, detracciones y percepciones, facturación en dólares, exportación.

## Criterios de finalización

- Boleta, factura y NC (incluida una con ISC) aceptadas en el entorno beta del PSE elegido.
- Escenarios `@critico` en verde con un PSE simulado y, antes del go-live, contra el sandbox del PSE.
- Cada RF-FAC tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- [NECESITA ACLARACIÓN] **PRD Q1:** ¿qué PSE/OSE? Define si UC-FAC-04 entra al MVP y quién genera el PDF.
- [NECESITA ACLARACIÓN] **Código de tipo de sistema ISC:** el contador indicó `01` (monto fijo); en el catálogo 08 de SUNAT el monto fijo es `02` y `01` es "al valor". Validar con un comprobante de prueba en el sandbox del PSE antes de S4.
- [NECESITA ACLARACIÓN] **Contador (PRD Q12):** plazo legal de envío a SUNAT, plazo de conservación de XML/CDR y si un comprobante rechazado se reemite con correlativo nuevo.
- [NECESITA ACLARACIÓN] **PRD T1:** dónde se guardan XML y CDR con respaldo (antes de S4).
