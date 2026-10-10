# language: es
@E02 @E02a @mvp
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

  @UC-CAT-04 @borde @RF-CAT-20
  Escenario: No se desactiva un granel con presentaciones activas
    Dado que "GRA-IPA" tiene presentaciones activas
    Cuando intento desactivar "GRA-IPA"
    Entonces la operación es rechazada con el mensaje "Desactiva primero las presentaciones de este granel"
