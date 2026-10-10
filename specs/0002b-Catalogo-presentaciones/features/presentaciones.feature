# language: es
@E02 @E02b @mvp
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

  @UC-CAT-03 @critico @RF-CAT-05 @RF-CAT-15 @RF-CAT-16
  Escenario: Crear presentación en botella con materiales fraccionados
    Cuando creo el producto terminado "TER-IPA-330" "IPA botella 330 ml" con:
      | campo           | valor   |
      | granel          | GRA-IPA |
      | contenido_l     | 0.3300  |
      | precio_venta    | 12.00   |
      | categoria_isc   | Cerveza |
      | vida_util_dias  | 120     |
    Y le asigno los materiales por unidad:
      | material    | cantidad |
      | ENV-BOT330  | 1        |
      | ENV-TAPA    | 1        |
      | ENV-ETQ-IPA | 1        |
      | ENV-CAJA24  | 0.0417   |
    Entonces la presentación "TER-IPA-330" queda activa y vendible
    Y controla lote

  @UC-CAT-03 @critico @RF-CAT-17
  Escenario: Un granel con varias presentaciones
    Dado que existe la presentación "TER-IPA-330" de "GRA-IPA"
    Cuando creo la presentación "TER-IPA-B20" "IPA barril 20 L" de "GRA-IPA" con contenido 20 L y material "ENV-PREC" × 1
    Entonces "GRA-IPA" tiene 2 presentaciones activas

  @UC-CAT-03 @borde @RF-CAT-15
  Escenario: Terminado sin materiales
    Cuando creo un producto terminado con granel "GRA-IPA" y contenido 0.330 L sin materiales
    Entonces la operación es rechazada con el mensaje "La presentación requiere al menos un material de envase"

  @UC-CAT-03 @borde @RF-CAT-11 @RF-CAT-15 @RF-CAT-16
  Esquema del escenario: Datos de presentación inválidos
    Cuando creo un producto terminado con "<campo>" igual a "<valor>"
    Entonces la operación es rechazada con el mensaje "<mensaje>"

    Ejemplos:
      | campo          | valor       | mensaje                                         |
      | contenido_l    | 0           | El contenido debe ser mayor a 0 litros          |
      | vida_util_dias | 0           | La vida útil debe ser mayor a 0 días            |
      | material       | INS-MALTA   | Los materiales deben ser productos tipo ENVASE  |
      | granel         | INS-MALTA   | El origen debe ser un producto tipo GRANEL      |

  @UC-CAT-03 @borde @RF-CAT-18
  Escenario: Cambiar materiales aplica solo a envasados futuros
    Dado que "TER-IPA-330" tiene stock 240 UND con costo promedio 4.200000
    Cuando cambio la etiqueta de "TER-IPA-330" por "ENV-ETQ-IPA2"
    Entonces el costo promedio de "TER-IPA-330" sigue siendo 4.200000
    Y el próximo envasado de "TER-IPA-330" consume "ENV-ETQ-IPA2"
