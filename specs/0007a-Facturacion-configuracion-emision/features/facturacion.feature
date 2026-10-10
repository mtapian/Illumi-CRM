# language: es
@E07 @E07a @mvp
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
