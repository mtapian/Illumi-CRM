# Spec 0007a — Facturación: configuración y emisión

Estado: borrador

Épica E07 (Facturación electrónica), parte 1 de 3. Depende de: 0006b, 0002c. La usan: 0007b, 0007c.

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

## Definiciones

- **Tipos de comprobante:** factura (`01`), boleta (`03`), nota de crédito (`07`) y comprobante interno (solo pruebas; rotulado "NO ES COMPROBANTE DE PAGO").

- **Series por defecto:** factura `F001`, boleta `B001`, NC de factura `FC01`, NC de boleta `BC01`. Cuatro caracteres alfanuméricos; las de factura y su NC empiezan con `F`, las de boleta y su NC con `B`.

- **Estados del comprobante:** `PENDIENTE` → `ACEPTADO` | `OBSERVADO` (aceptado con observaciones) | `RECHAZADO` | `ERROR` (falla de comunicación). Las NC tienen además `ESPERANDO_ORIGINAL` y `NO_REQUERIDA`.

- **ISC de la cerveza** (PRD Q2, respondido por el contador): Sistema Específico, **S/ 2.51 por litro desde el 2024-07-01**, sin importar el precio ni la graduación. Se configura por empresa en categorías de ISC con tarifas por vigencia (épica 0002, UC-CAT-05). Base del IGV = valor + ISC; IGV = (valor + ISC) × 18 %; total = valor + ISC + IGV. En el comprobante: tributo `2000` y el código de tipo de sistema de la categoría.

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

- RF-FAC-07: CUANDO se registra una venta (épica 0006), EL SISTEMA crea su comprobante `PENDIENTE` con un correlativo por serie sin huecos ni duplicados, aunque el proceso se caiga justo después de guardar la venta (RN-FAC-02).
- RF-FAC-08: CUANDO el comprobante se envía al PSE, EL SISTEMA guarda el estado de la respuesta, el código, el mensaje, el hash, el PDF y **una copia propia** del XML y del CDR (RN-FAC-09).
- RF-FAC-09: SI el PSE o SUNAT no responden, ENTONCES EL SISTEMA deja el comprobante en `ERROR`, cuenta el intento y la venta sigue registrada.
- RF-FAC-10: CUANDO un comprobante queda `ACEPTADO`, EL SISTEMA registra la fecha y hora de aceptación (para la métrica de 24 h del PRD §8) y no permite modificarlo; solo se corrige con una NC (RN-FAC-03).
- RF-FAC-11: EL SISTEMA exige cliente con RUC en una factura; en una boleta aplica la regla de identificación de la épica 0006 (RN-FAC-01).
- RF-FAC-12: CUANDO una línea tiene ISC, EL SISTEMA lo informa con el tributo `2000`, el código de tipo de sistema de su categoría y la base del IGV = valor + ISC (RN-FAC-07).
- RF-FAC-13: CUANDO una línea es una entrega gratuita, EL SISTEMA la informa como transferencia gratuita con su valor referencial, ISC e IGV, y total cobrado 0 (RN-FAC-11).
- RF-FAC-14: EL SISTEMA genera la representación impresa en A4 y en ticket de 80 mm, con datos del emisor y del cliente, líneas, totales, importe en letras, hash o código QR y la leyenda de representación impresa.

## Requisitos no funcionales

- RNF-FAC-01: XML y CDR se conservan durante el plazo legal (configurable con fecha de vigencia; por defecto 5 años) en un almacenamiento con respaldo, sin opción de borrado.

## Casos límite

- **Tarifa de ISC sin vigencia** a la fecha de emisión: la venta se rechaza (épica 0002).

## Fuera de alcance

Firma directa con SUNAT, guía de remisión, notas de débito, NC parciales (por línea o descuento), motivos del catálogo 09 distintos de 01, 02 y 06, comunicación de baja, detracciones y percepciones, facturación en dólares, exportación.

## Criterios de finalización

- Boleta, factura y NC (incluida una con ISC) aceptadas en el entorno beta del PSE elegido.
- Escenarios de `features/` en verde.
- Cada RF de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- [NECESITA ACLARACIÓN] **PRD Q1:** ¿qué PSE/OSE? Define si UC-FAC-04 entra al MVP y quién genera el PDF.
- [NECESITA ACLARACIÓN] **Código de tipo de sistema ISC:** el contador indicó `01` (monto fijo); en el catálogo 08 de SUNAT el monto fijo es `02` y `01` es "al valor". Validar con un comprobante de prueba en el sandbox del PSE antes de S4.
- [NECESITA ACLARACIÓN] **PRD T1:** dónde se guardan XML y CDR con respaldo (antes de S4).
