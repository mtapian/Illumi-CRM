# language: es
@E02 @E02c @mvp
Característica: ISC de un producto que se vende
  Como responsable del catálogo
  Quiero que un producto con ISC por litro tenga su contenido en litros
  Para que el ISC de cada venta se calcule bien

  Antecedentes:
    Dado que soy usuario "administrador" de "Cervecería Andina"
    Y existen las unidades "UND, KG, G, L"

  @UC-CAT-02 @RN-CAT-10 @borde @RF-CAT-26 @RF-CAT-45
  Escenario: Un producto que se vende con ISC requiere contenido en litros
    Cuando creo el bien "MER-CERV-TERCERO" que se vende afecto a ISC y sin contenido en litros
    Entonces la operación es rechazada con el mensaje "Un producto con ISC por litro requiere el contenido en litros por unidad"
