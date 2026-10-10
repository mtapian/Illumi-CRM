# language: es
@E07 @mvp
Característica: Emisión, reintento y anulación de comprobantes electrónicos
  Como administrador de la cervecera
  Quiero que cada venta emita su comprobante ante SUNAT sin pasos manuales
  Para cumplir con la normativa sin frenar la operación

  Antecedentes:
    Dado que "Cervecería Andina" tiene la facturación habilitada en entorno "beta"
    Y las series "F001" factura, "B001" boleta, "FC01" NC de factura y "BC01" NC de boleta
    Y el último correlativo de "B001" es 41
    Y el PSE está disponible

  @UC-FAC-01 @borde @RF-FAC-01
  Esquema del escenario: Validación de series
    Cuando configuro la serie de "<tipo>" como "<serie>"
    Entonces el resultado es "<resultado>"

    Ejemplos:
      | tipo           | serie | resultado                                        |
      | factura        | F002  | guardado                                         |
      | factura        | B002  | La serie de factura debe empezar con F           |
      | NC de boleta   | FC01  | La serie de NC de boleta debe empezar con B      |
      | boleta         | B0001 | La serie debe tener 4 caracteres                 |

  @UC-FAC-01 @RF-FAC-03
  Escenario: Probar conexión con el PSE
    Cuando presiono "Probar conexión"
    Entonces veo el resultado "Conexión correcta" con fecha y hora
    Y la contraseña de las credenciales se muestra enmascarada

  @UC-FAC-02 @critico @RF-FAC-07 @RF-FAC-08 @RF-FAC-10
  Escenario: Venta con boleta emite el comprobante aceptado
    Cuando se registra la venta "V-000001" con "BOLETA" por 288.00
    Entonces se crea el comprobante "B001-00000042" vinculado a "V-000001"
    Y su estado final es "ACEPTADO"
    Y se guardan el XML, el CDR, el PDF y el hash

  @UC-FAC-02 @critico @RF-FAC-09
  Escenario: Caída del PSE no impide la venta
    Dado que el PSE no responde
    Cuando se registra la venta "V-000002" con "BOLETA" por 120.00
    Entonces la venta "V-000002" queda "EMITIDA"
    Y el comprobante "B001-00000042" queda en estado "ERROR" con 1 intento

  @UC-FAC-03 @critico @RF-FAC-07 @RF-FAC-15
  Escenario: El reintento usa el mismo correlativo
    Dado el comprobante "B001-00000042" en estado "ERROR" con 1 intento
    Cuando el PSE vuelve a estar disponible
    Y se ejecuta el proceso de reintentos
    Entonces el comprobante "B001-00000042" queda "ACEPTADO"
    Y no se generó ningún otro correlativo

  @UC-FAC-03 @borde @RF-FAC-18
  Escenario: Reintentos agotados requieren atención
    Dado el comprobante "B001-00000042" en estado "ERROR" con 10 intentos
    Cuando se ejecuta el proceso de reintentos
    Entonces el comprobante aparece como "Requiere atención" en la bandeja y en el dashboard
    Y se sigue reintentando cada hora hasta enviarse o hasta que venza el plazo legal

  @UC-FAC-03 @borde @RF-FAC-16
  Escenario: Respuesta tardía del primer envío
    Dado el comprobante "B001-00000042" en estado "ERROR" que SUNAT ya aceptó
    Cuando se ejecuta el proceso de reintentos
    Entonces se consulta el estado en el PSE antes de reenviar
    Y el comprobante queda "ACEPTADO" sin reenviarse

  @UC-FAC-03 @borde @RF-FAC-21
  Escenario: Un comprobante rechazado no se reintenta
    Dado el comprobante "B001-00000043" en estado "RECHAZADO" con el mensaje del PSE
    Cuando se ejecuta el proceso de reintentos
    Entonces el comprobante sigue "RECHAZADO"
    Y la bandeja ofrece la acción "Reemitir"

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

  @UC-FAC-03 @RN-FAC-08 @borde @RF-FAC-19
  Escenario: Alerta por plazo legal de envío
    Dado que el plazo de envío a SUNAT es de 3 días
    Y el comprobante "B001-00000042" emitido el "2026-12-01" en estado "ERROR"
    Cuando la fecha es "2026-12-03"
    Entonces el comprobante aparece como "Requiere atención: vence el plazo de envío en 1 día"
    Y al reintentarse conserva la fecha de emisión "2026-12-01"

  @UC-FAC-04 @pendiente-q1 @RF-FAC-22
  Escenario: Resumen diario de boletas y sus NC
    Dado que el PSE elegido exige que el emisor envíe el resumen diario
    Y el "2026-12-01" se emitieron las boletas "B001-00000042" y "B001-00000043" y la NC "BC01-00000001"
    Cuando se ejecuta el resumen diario el "2026-12-02" a la 01:00
    Entonces se envía un resumen con los 3 comprobantes y se registra el ticket
    Y al consultar el ticket con respuesta aceptada, los 3 comprobantes quedan "ACEPTADO"

  @UC-FAC-06 @RF-FAC-30
  Escenario: Envío automático al cliente
    Dado que el envío automático por email está activado
    Y el cliente "Bar El Lúpulo" tiene email "compras@ellupulo.pe"
    Cuando el comprobante "F001-00000007" queda "ACEPTADO"
    Entonces se envía un email a "compras@ellupulo.pe" con el PDF y el XML adjuntos
    Y se registra la fecha de envío

  @UC-FAC-01 @borde @RF-FAC-04
  Escenario: Facturación deshabilitada en trial emite un comprobante interno
    Dado que la empresa está en "trial" y la facturación está deshabilitada
    Cuando se registra una venta con "BOLETA"
    Entonces se emite un comprobante interno "I001" rotulado "NO ES COMPROBANTE DE PAGO"
    Y no se llama al PSE

  @UC-FAC-01 @borde @RF-FAC-05
  Escenario: Empresa activa sin facturación habilitada deja el comprobante pendiente
    Dado que la empresa está "activa" y la facturación está deshabilitada
    Cuando se registra una venta con "BOLETA"
    Entonces el comprobante "B001-00000042" queda "PENDIENTE"
    Y al habilitar la facturación se envía con su fecha de emisión original

  @UC-FAC-02 @RN-FAC-07 @critico @RF-FAC-12
  Escenario: Boleta de cerveza con ISC de sistema específico
    Dado la categoría de ISC "Cerveza" con tarifa de S/ 2.51 por litro vigente desde "2024-07-01"
    Y "TER-IPA-330" con categoría de ISC "Cerveza" y contenido 0.33 L
    Cuando se registra la venta "V-000001" con "BOLETA" de 24 unidades de "TER-IPA-330" a 12.00
    Entonces el comprobante "B001-00000042" informa:
      | litros | isc   | valor_venta | igv   | total  |
      | 7.92   | 19.88 | 224.19      | 43.93 | 288.00 |
    Y el ISC va con el código de tributo "2000" y el código de tipo de sistema configurado

  @UC-FAC-02 @RN-FAC-07 @borde @RF-FAC-12 @RF-CAT-25
  Escenario: Producto con categoría de ISC sin tarifa vigente
    Dado la categoría de ISC "Cerveza" cuya primera tarifa rige desde "2024-07-01"
    Cuando se registra una venta de "TER-IPA-330" con fecha de emisión "2024-06-30"
    Entonces la operación es rechazada con el mensaje "La categoría de ISC Cerveza no tiene tarifa vigente al 2024-06-30"

  @UC-FAC-02 @RN-FAC-11 @borde @RF-FAC-13 @RF-VEN-30
  Escenario: Entrega gratuita como retiro de bienes con ISC e IGV
    Dado la categoría de ISC "Cerveza" con tarifa de S/ 2.51 por litro vigente
    Y "TER-IPA-BARRIL" con categoría de ISC "Cerveza" y contenido 20 L
    Cuando se registra una entrega gratuita de 5 unidades de "TER-IPA-BARRIL" con valor referencial 100.00 por unidad y motivo "Promoción"
    Entonces el comprobante informa una transferencia gratuita con valor referencial 500.00, ISC 251.00 e IGV 135.18
    Y el total cobrado al cliente es 0.00

  @UC-FAC-05 @RN-FAC-10 @borde @RF-FAC-27
  Escenario: La nota de crédito total replica el ISC del comprobante original
    Dado la boleta "B001-00000042" aceptada con ISC 19.88, valor 224.19 e IGV 43.93
    Cuando se anula la venta con motivo SUNAT "06 Devolución total"
    Entonces la nota de crédito "BC01-00000001" informa ISC 19.88, valor 224.19 e IGV 43.93
