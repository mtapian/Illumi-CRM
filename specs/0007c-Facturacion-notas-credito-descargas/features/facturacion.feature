# language: es
@E07 @E07c @mvp
Característica: Emisión, reintento y anulación de comprobantes electrónicos
  Como administrador de la cervecera
  Quiero que cada venta emita su comprobante ante SUNAT sin pasos manuales
  Para cumplir con la normativa sin frenar la operación

  Antecedentes:
    Dado que "Cervecería Andina" tiene la facturación habilitada en entorno "beta"
    Y las series "F001" factura, "B001" boleta, "FC01" NC de factura y "BC01" NC de boleta
    Y el último correlativo de "B001" es 41
    Y el PSE está disponible

  @UC-FAC-05 @critico @RF-FAC-24
  Escenario: Anular una venta con factura emite una nota de crédito
    Dado la venta "V-000010" con la factura "F001-00000007" en estado "ACEPTADO" por 1056.00
    Cuando se anula la venta "V-000010" con motivo SUNAT "06 Devolución total"
    Entonces se emite la nota de crédito "FC01-00000001" que referencia "F001-00000007" por 1056.00 con tipo "06"
    Y su estado final es "ACEPTADO"

  @UC-FAC-05 @borde @RF-FAC-25
  Escenario: La NC espera a que el comprobante original sea aceptado
    Dado la venta "V-000002" con el comprobante "B001-00000042" en estado "ERROR"
    Cuando se anula la venta "V-000002" con motivo SUNAT "01 Anulación de la operación"
    Entonces "V-000002" queda "ANULADA" y su stock se revierte de inmediato
    Y la nota de crédito queda "ESPERANDO_ORIGINAL" sin enviarse al PSE
    Y la bandeja muestra el par para resolverlo
    Cuando "B001-00000042" queda "ACEPTADO" en el proceso de reintentos
    Entonces la nota de crédito "BC01-00000001" se envía y queda "ACEPTADO"

  @UC-FAC-05 @borde @RF-FAC-26
  Escenario: Sin NC si el comprobante original fue rechazado
    Dado la venta anulada "V-000003" con NC "ESPERANDO_ORIGINAL" y su comprobante "B001-00000043" en estado "RECHAZADO"
    Cuando se ejecuta el proceso de reintentos
    Entonces la nota de crédito queda "NO_REQUERIDA"

  @UC-FAC-06 @RF-FAC-30
  Escenario: Envío automático al cliente
    Dado que el envío automático por email está activado
    Y el cliente "Bar El Lúpulo" tiene email "compras@ellupulo.pe"
    Cuando el comprobante "F001-00000007" queda "ACEPTADO"
    Entonces se envía un email a "compras@ellupulo.pe" con el PDF y el XML adjuntos
    Y se registra la fecha de envío

  @UC-FAC-05 @RN-FAC-10 @borde @RF-FAC-27
  Escenario: La nota de crédito total replica el ISC del comprobante original
    Dado la boleta "B001-00000042" aceptada con ISC 19.88, valor 224.19 e IGV 43.93
    Cuando se anula la venta con motivo SUNAT "06 Devolución total"
    Entonces la nota de crédito "BC01-00000001" informa ISC 19.88, valor 224.19 e IGV 43.93

  @UC-FAC-06 @borde @RF-FAC-32 @RF-FAC-21
  Escenario: Las ventas con comprobante rechazado sin reemitir quedan señaladas
    Dado la venta "V-000009" con la boleta "B001-00000050" en estado "RECHAZADO"
    Cuando el gerente abre la bandeja de comprobantes
    Entonces ve "V-000009" en "Requiere atención: comprobante rechazado sin reemitir"
    Y el dashboard muestra 1 venta con comprobante rechazado
    Cuando se reemite el comprobante de "V-000009" con el correlativo "B001-00000051" y queda "ACEPTADO"
    Entonces "V-000009" deja de aparecer como pendiente de reemisión
