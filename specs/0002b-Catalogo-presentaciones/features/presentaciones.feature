# language: es
@E02 @E02b @mvp
Característica: Receta de un bien que se fabrica
  Como maestro cervecero
  Quiero definir, si lo necesito, la receta de cada bien que fabrico con cualquier producto del catálogo
  Para que la orden de producción la copie y calcule el costo real
  (Antes "presentaciones": reformulada por la enmienda 4 de 0002a, RF-CAT-41.)

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

  @UC-CAT-03 @critico @RF-CAT-41
  Escenario: Bien que se fabrica y se vende, con receta de varios componentes
    Cuando creo el bien "TER-IPA-330" "IPA botella 330 ml" que se fabrica y se vende con:
      | campo           | valor   |
      | precio_venta    | 12.00   |
      | vida_util_dias  | 120     |
    Y le asigno la receta por unidad:
      | componente  | cantidad |
      | GRA-IPA     | 0.3300   |
      | ENV-BOT330  | 1        |
      | ENV-TAPA    | 1        |
      | ENV-ETQ-IPA | 1        |
      | ENV-CAJA24  | 0.0417   |
    Entonces "TER-IPA-330" queda activo y vendible con 5 componentes en su receta

  @UC-CAT-03 @critico @RF-CAT-41
  Escenario: Un mismo granel en las recetas de varios productos
    Dado que existe el bien "TER-IPA-330" con "GRA-IPA" en su receta
    Cuando creo el bien "TER-IPA-B20" "IPA barril 20 L" que se fabrica con receta "GRA-IPA" × 20 y "ENV-PREC" × 1
    Entonces "GRA-IPA" está en la receta de 2 productos activos

  @UC-CAT-03 @RF-CAT-41
  Escenario: La receta es opcional
    Cuando creo el bien "TER-IPA-LATA" "IPA lata" que se fabrica y se vende sin receta
    Entonces "TER-IPA-LATA" se crea sin receta

  @UC-CAT-03 @borde @RF-CAT-40 @RF-CAT-41
  Esquema del escenario: Datos de receta inválidos
    Cuando creo un bien que se fabrica con "<campo>" igual a "<valor>"
    Entonces la operación es rechazada con el mensaje "<mensaje>"

    Ejemplos:
      | campo          | valor      | mensaje                                            |
      | cantidad       | 0          | La cantidad de cada componente debe ser mayor a 0  |
      | vida_util_dias | 0          | La vida útil debe ser mayor a 0 días               |
      | repetido       | ENV-BOT330 | Un componente está repetido en la receta           |
      | inactivo       | ENV-PREC   | Un componente no existe o está inactivo            |

  @UC-CAT-03 @borde @RF-CAT-18
  Escenario: Cambiar la receta aplica solo a producciones futuras
    Dado que "TER-IPA-330" tiene stock 240 UND con costo promedio 4.200000
    Cuando cambio la etiqueta en la receta de "TER-IPA-330" por "ENV-ETQ-IPA2"
    Entonces el costo promedio de "TER-IPA-330" sigue siendo 4.200000
    Y la próxima producción de "TER-IPA-330" consume "ENV-ETQ-IPA2"
