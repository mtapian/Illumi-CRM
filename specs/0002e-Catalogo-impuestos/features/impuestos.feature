# language: es
@E02 @E02e @mvp @borrador
Característica: Impuestos de la empresa y del producto
  Como administrador
  Quiero registrar mis impuestos con tasas por vigencia y asignarlos a cada producto
  Para que cada venta y comprobante calcule bien el IGV y el ISC

  Antecedentes:
    Dado que soy usuario "administrador" de "Cervecería Andina"

  @UC-CAT-09 @critico @RF-CAT-52
  Escenario: Una empresa nueva trae sus impuestos iniciales
    Entonces la empresa tiene los impuestos "IGV 18%", "Exonerado" e "Inafecto"

  @UC-CAT-09 @critico @RF-CAT-53
  Escenario: El usuario define sus impuestos con código SUNAT y criterio
    Cuando defino los impuestos:
      | nombre         | código | criterio   | tasa  | desde      |
      | ISC por 750 ml | ISC    | monto fijo | 2.01  | 2026-01-01 |
      | ISC por galón  | ISC    | monto fijo | 10.94 | 2026-01-01 |
    Entonces el impuesto "ISC por 750 ml" se informa en el comprobante con el sistema "02"

  @UC-CAT-09 @borde @RF-CAT-53
  Escenario: El IGV no admite monto fijo
    Cuando defino el impuesto "IGV fijo" con código "IGV" y criterio "monto fijo"
    Entonces la operación es rechazada con el mensaje "Solo el ISC admite monto fijo"

  @UC-CAT-09 @critico @RF-CAT-54 @RF-CAT-59
  Escenario: Un cambio de tasa aplica desde su fecha
    Dado el impuesto "ISC por 750 ml" de monto fijo 2.01 desde "2026-01-01"
    Cuando agrego al impuesto "ISC por 750 ml" la tasa 2.20 desde "2027-01-01"
    Entonces la tasa de "ISC por 750 ml" es 2.01 el "2026-12-31" y 2.20 el "2027-01-01"

  @UC-CAT-09 @borde @RF-CAT-54
  Esquema del escenario: Tasa inválida
    Cuando agrego al impuesto "<impuesto>" la tasa <importe> desde "<fecha>"
    Entonces la operación es rechazada con el mensaje "<mensaje>"

    Ejemplos:
      | impuesto  | importe | fecha      | mensaje                                         |
      | Exonerado | 18      | 2027-01-01 | Un impuesto exonerado o inafecto tiene tasa 0   |
      | IGV 18%   | -1      | 2027-01-01 | La tasa no puede ser negativa                   |

  @UC-CAT-10 @critico @RF-CAT-57 @RF-CAT-59
  Escenario: Producto exonerado no lleva IGV
    Dado el bien "LIB-001" que se vende a 50.00 con impuesto de venta "Exonerado"
    Entonces el desglose de "LIB-001" es valor 50.00, ISC 0.00 e IGV 0.00

  @UC-CAT-10 @critico @RF-CAT-58 @RF-CAT-59
  Escenario: Cerveza con IGV e ISC de monto fijo
    Dado el impuesto "ISC 330 ml" de monto fijo 0.8283 desde "2024-07-01"
    Y el bien "TER-IPA-330" que se vende a 12.00 con impuestos de venta "IGV 18%" e "ISC 330 ml"
    Entonces una venta de 24 "TER-IPA-330" se desglosa en valor 224.19, ISC 19.88 e IGV 43.93

  @UC-CAT-10 @borde @RF-CAT-57 @RF-CAT-58
  Esquema del escenario: Impuestos de venta inválidos
    Cuando creo el <tipo> "X-1" que se vende con impuestos de venta "<impuestos>"
    Entonces la operación es rechazada con el mensaje "<mensaje>"

    Ejemplos:
      | tipo     | impuestos               | mensaje                                                          |
      | bien     | ISC 330 ml              | El producto debe tener un impuesto de IGV, exonerado o inafecto  |
      | bien     | IGV 18%, Exonerado      | El producto debe tener un impuesto de IGV, exonerado o inafecto  |
      | servicio | IGV 18%, ISC 330 ml     | Un servicio no lleva ISC                                         |

  @UC-CAT-09 @borde @RF-CAT-55
  Escenario: Un impuesto asignado no se desactiva
    Dado el bien "TER-IPA-330" con impuesto de venta "IGV 18%"
    Cuando intento desactivar el impuesto "IGV 18%"
    Entonces la operación es rechazada con el mensaje "El impuesto está asignado a productos activos"
