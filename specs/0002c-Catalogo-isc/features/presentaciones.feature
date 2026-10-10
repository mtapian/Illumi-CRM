# language: es
@E02 @E02c @mvp
Característica: Presentaciones de producto terminado
  Como maestro cervecero
  Quiero definir cada presentación con su granel, contenido y materiales
  Para que el envasado descuente lo correcto y calcule el costo unitario

  Antecedentes:
    Dado que soy usuario "produccion" de "Cervecería Andina"
    Y existe el granel "GRA-IPA" (IPA a granel)
    Y existen los envases:
      | sku         | nombre                |
      | ENV-BOT330  | Botella ámbar 330 ml  |
      | ENV-TAPA    | Tapa corona           |
      | ENV-ETQ-IPA | Etiqueta IPA          |
      | ENV-CAJA24  | Caja x24              |
      | ENV-PREC    | Precinto de barril    |

  @UC-CAT-05 @RN-CAT-10 @critico @RF-CAT-22 @RF-CAT-23 @RF-CAT-24 @RF-CAT-25
  Escenario: Tarifa de ISC configurable por empresa con vigencia
    Dado la categoría de ISC "Cerveza" con Sistema Específico
    Y la tarifa de S/ 2.51 por litro vigente desde "2024-07-01"
    Cuando agrego a "Cerveza" la tarifa de S/ 2.70 por litro vigente desde "2027-01-01"
    Entonces una venta de "TER-IPA-330" emitida el "2026-12-31" usa S/ 2.51 por litro
    Y una venta emitida el "2027-01-01" usa S/ 2.70 por litro

  @UC-CAT-05 @borde @RF-CAT-27
  Escenario: Producto sin categoría de ISC no paga ISC
    Dado el producto terminado "TER-SIN-ISC-330" sin categoría de ISC
    Cuando se calcula el ISC de una venta de 10 unidades de "TER-SIN-ISC-330"
    Entonces el ISC es 0.00
