# language: es
@E02 @E02c @mvp
Característica: Tasas de ISC de cada producto, con vigencia
  Como administrador
  Quiero registrar en la ficha de cada producto su tasa de ISC con su fecha de vigencia
  Para que cada venta use la tarifa vigente a su fecha de emisión

  Antecedentes:
    Dado que soy usuario "produccion" de "Cervecería Andina"
    Y existe el bien que se fabrica "GRA-IPA" (IPA a granel)
    Y existen los bienes que se compran:
      | sku         | nombre                |
      | ENV-BOT330  | Botella ámbar 330 ml  |
      | ENV-TAPA    | Tapa corona           |
      | ENV-ETQ-IPA | Etiqueta IPA          |
      | ENV-CAJA24  | Caja x24              |
      | ENV-PREC    | Precinto de barril    |

  @UC-CAT-05 @RN-CAT-10 @critico @RF-CAT-23 @RF-CAT-24 @RF-CAT-25 @RF-CAT-45 @RF-CAT-46
  Escenario: Tasa de ISC del producto con vigencia
    Dado el bien "TER-IPA-330" afecto a ISC con tasa de S/ 2.51 por litro vigente desde "2024-07-01"
    Cuando agrego a "TER-IPA-330" la tasa de S/ 2.70 por litro vigente desde "2027-01-01"
    Entonces una venta de "TER-IPA-330" emitida el "2026-12-31" usa S/ 2.51 por litro
    Y una venta emitida el "2027-01-01" usa S/ 2.70 por litro

  @UC-CAT-05 @borde @RF-CAT-27
  Escenario: Un producto no afecto a ISC no paga ISC
    Dado el bien "TER-SIN-ISC-330" que se vende sin ISC
    Cuando se calcula el ISC de una venta de 10 unidades de "TER-SIN-ISC-330"
    Entonces el ISC es 0.00
