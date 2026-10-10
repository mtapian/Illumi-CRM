# language: es
@E07 @E07b @mvp
Característica: Emisión, reintento y anulación de comprobantes electrónicos
  Como administrador de la cervecera
  Quiero que cada venta emita su comprobante ante SUNAT sin pasos manuales
  Para cumplir con la normativa sin frenar la operación

  Antecedentes:
    Dado que "Cervecería Andina" tiene la facturación habilitada en entorno "beta"
    Y las series "F001" factura, "B001" boleta, "FC01" NC de factura y "BC01" NC de boleta
    Y el último correlativo de "B001" es 41
    Y el PSE está disponible

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

  @UC-FAC-03 @borde @RF-FAC-17
  Escenario: Dos reintentos simultáneos envían el comprobante una sola vez
    Dado el comprobante "B001-00000042" en estado "ERROR"
    Cuando el cron de reintentos y un usuario desde la bandeja lo reintentan al mismo tiempo
    Entonces el PSE recibe un solo envío de "B001-00000042"
