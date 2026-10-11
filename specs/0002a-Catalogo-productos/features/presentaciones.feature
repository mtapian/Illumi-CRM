# language: es
@E02 @E02a @mvp
Característica: Desactivar o eliminar un producto usado en recetas
  Como maestro cervecero
  Quiero desactivar productos que ya no uso aunque estén en una receta
  Para no ofrecerlos más, sin perder la receta ni su historial

  Antecedentes:
    Dado que soy usuario "produccion" de "Cervecería Andina"
    Y existe el bien que se fabrica "GRA-IPA" (IPA a granel)
    Y existen los bienes que se compran:
      | sku         | nombre                |
      | ENV-BOT330  | Botella ámbar 330 ml  |

  @UC-CAT-04 @borde @RF-CAT-20 @RF-CAT-21
  Escenario: Un componente de una receta se desactiva pero no se elimina
    Dado que existe el bien "TER-IPA-330" con "GRA-IPA" en su receta
    Cuando intento eliminar "GRA-IPA"
    Entonces la operación es rechazada con el mensaje "El producto tiene historial; solo puede desactivarse"
    Cuando intento desactivar "GRA-IPA"
    Entonces "GRA-IPA" queda inactivo y sigue en la receta de "TER-IPA-330"
