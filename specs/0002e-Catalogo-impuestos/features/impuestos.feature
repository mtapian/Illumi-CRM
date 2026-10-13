# language: es
@E02 @E02e @mvp
Característica: Impuestos de venta y de compra
  Como administrador
  Quiero registrar mis impuestos de venta y de compra con tasas por vigencia y asignarlos a cada producto
  Para que cada venta, compra y comprobante calcule bien el IGV y el ISC

  Antecedentes:
    Dado que soy usuario "administrador" de "Cervecería Andina"

  @UC-CAT-09 @critico @RF-CAT-52
  Escenario: Una empresa nueva trae sus impuestos iniciales
    Entonces la empresa tiene los impuestos:
      | nombre    | tipo   | código |
      | IGV 18%   | Venta  | IGV    |
      | Exonerado | Venta  | EXO    |
      | Inafecto  | Venta  | INA    |
      | IGV 18%   | Compra | IGV    |
      | Exonerado | Compra | EXO    |
      | Inafecto  | Compra | INA    |

  @UC-CAT-09 @critico @RF-CAT-53 @RF-CAT-54
  Escenario: El usuario define sus impuestos de ISC
    Cuando defino los impuestos:
      | nombre         | tipo  | código | tasa  | desde      |
      | ISC por 750 ml | Venta | ISC    | 2.01  | 2026-01-01 |
      | ISC por galón  | Venta | ISC    | 10.94 | 2026-01-01 |
    Entonces la tasa de "ISC por 750 ml" es 2.01 el "2026-01-01"

  @UC-CAT-09 @borde @RF-CAT-53
  Escenario: El ISC es solo un impuesto de venta
    Cuando defino el impuesto "ISC compra" de tipo "Compra" con código "ISC"
    Entonces la operación es rechazada con el mensaje "El ISC es solo un impuesto de venta"

  @UC-CAT-09 @critico @RF-CAT-54 @RF-CAT-59
  Escenario: Un cambio de tasa aplica desde su fecha
    Dado el impuesto "ISC por 750 ml" de monto fijo 2.01 desde "2026-01-01"
    Cuando agrego al impuesto "ISC por 750 ml" la tasa 2.20 desde "2027-01-01"
    Entonces la tasa de "ISC por 750 ml" es 2.01 el "2026-12-31" y 2.20 el "2027-01-01"

  @UC-CAT-09 @borde @RF-CAT-54
  Esquema del escenario: Tasa inválida
    Cuando agrego al impuesto "<impuesto>" de venta la tasa <importe> desde "<fecha>"
    Entonces la operación es rechazada con el mensaje "<mensaje>"

    Ejemplos:
      | impuesto  | importe | fecha      | mensaje                                       |
      | Exonerado | 18      | 2027-01-01 | Un impuesto exonerado o inafecto tiene tasa 0 |
      | IGV 18%   | -1      | 2027-01-01 | La tasa no puede ser negativa                 |

  @UC-CAT-10 @critico @RF-CAT-57 @RF-CAT-59
  Escenario: Producto exonerado no lleva IGV
    Dado el bien "LIB-001" que se vende a 50.00 con impuesto de venta "Exonerado"
    Entonces el desglose de "LIB-001" es valor 50.00, ISC 0.00 e IGV 0.00

  @UC-CAT-10 @critico @RF-CAT-58 @RF-CAT-59
  Escenario: Cerveza con IGV e ISC por unidad
    Dado el impuesto "ISC 330 ml" de monto fijo 0.8283 desde "2024-07-01"
    Y el bien "TER-IPA-330" que se vende a 12.00 con impuestos de venta "IGV 18%" e "ISC 330 ml"
    Entonces una venta de 24 "TER-IPA-330" se desglosa en valor 224.19, ISC 19.88 e IGV 43.93

  @UC-CAT-10 @borde @RF-CAT-57 @RF-CAT-58
  Esquema del escenario: Impuestos del producto inválidos
    Cuando creo el <tipo> "X-1" con impuestos de <lista> "<impuestos>"
    Entonces la operación es rechazada con el mensaje "<mensaje>"

    Ejemplos:
      | tipo     | lista  | impuestos           | mensaje                                                         |
      | bien     | venta  | ISC 330 ml          | El producto debe tener un impuesto de IGV, exonerado o inafecto |
      | bien     | venta  | IGV 18%, Exonerado  | El producto debe tener un impuesto de IGV, exonerado o inafecto |
      | bien     | compra | IGV 18%, Inafecto   | El producto debe tener un impuesto de IGV, exonerado o inafecto |
      | servicio | venta  | IGV 18%, ISC 330 ml | Un servicio no lleva ISC                                        |

  @UC-CAT-10 @critico @RF-CAT-53 @RF-CAT-59
  Escenario: ISC porcentual elegido por el usuario (enmienda 1)
    Dado el impuesto "ISC 25%" de venta con criterio "porcentaje" y tasa 25 desde "2026-01-01"
    Y el bien "LIC-001" que se vende a 100.00 con impuestos de venta "IGV 18%" e "ISC 25%"
    Entonces el desglose de "LIC-001" es valor 67.80, ISC 16.95 e IGV 15.25

  @UC-CAT-10 @critico @RF-CAT-61
  Escenario: Insumo exonerado comprado con factura no lleva IGV
    Dado el bien "INS-001" que se compra con impuesto de compra "Exonerado"
    Y el bien "INS-002" que se compra con impuesto de compra "IGV 18%"
    Cuando registro una compra con factura de 10 "INS-001" a 5.00 y 10 "INS-002" a 5.00
    Entonces la compra tiene subtotal 100.00, IGV 9.00 y total 109.00

  @UC-CAT-09 @borde @RF-CAT-55
  Escenario: Un impuesto asignado no se desactiva
    Dado el bien "TER-IPA-330" con impuesto de venta "IGV 18%"
    Cuando intento desactivar el impuesto "IGV 18%" de venta
    Entonces la operación es rechazada con el mensaje "El impuesto está asignado a productos activos"
