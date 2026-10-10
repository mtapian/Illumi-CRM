# language: es
@E02 @E02c @mvp
Característica: Gestión de productos por tipo
  Como responsable de almacén o producción
  Quiero registrar insumos, envases, graneles y presentaciones
  Para que compras, producción y ventas usen un catálogo único

  Antecedentes:
    Dado que soy usuario "gerente" de "Cervecería Andina"
    Y existen las unidades "UND, KG, G, L"

  @UC-CAT-02 @RN-CAT-10 @borde @RF-CAT-26
  Escenario: Mercadería con ISC requiere contenido en litros
    Cuando creo el producto "MER-CERV-TERCERO" de tipo "MERCADERIA" con categoría de ISC "Cerveza" y sin contenido en litros
    Entonces la operación es rechazada con el mensaje "Un producto con ISC por litro requiere el contenido en litros por unidad"
