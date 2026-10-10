# language: es
@E02 @mvp
Característica: Gestión de productos por tipo
  Como responsable de almacén o producción
  Quiero registrar insumos, envases, graneles y presentaciones
  Para que compras, producción y ventas usen un catálogo único

  Antecedentes:
    Dado que soy usuario "gerente" de "Cervecería Andina"
    Y existen las unidades "UND, KG, G, L"

  @UC-CAT-02 @critico @RF-CAT-04 @RF-CAT-07 @RF-CAT-12
  Esquema del escenario: Crear productos de cada tipo
    Cuando creo un producto con SKU "<sku>", nombre "<nombre>", tipo "<tipo>" y unidad "<unidad>"
    Entonces el producto "<sku>" queda activo con stock 0
    Y controla lote es "<lote>"

    Ejemplos:
      | sku        | nombre                 | tipo    | unidad | lote |
      | INS-MALTA  | Malta Pilsen           | INSUMO  | KG     | no   |
      | INS-LUP-CS | Lúpulo Cascade         | INSUMO  | G      | no   |
      | ENV-BOT330 | Botella ámbar 330 ml   | ENVASE  | UND    | no   |
      | GRA-IPA    | IPA a granel           | GRANEL  | L      | sí   |

  @UC-CAT-02 @borde @RF-CAT-07
  Escenario: Granel con unidad distinta a litros
    Cuando creo un producto tipo "GRANEL" con unidad "KG"
    Entonces la operación es rechazada con el mensaje "El granel debe medirse en litros"

  @UC-CAT-02 @borde @RF-CAT-08
  Escenario: SKU duplicado en la misma empresa
    Dado que existe el producto con SKU "INS-MALTA"
    Cuando creo otro producto con SKU "INS-MALTA"
    Entonces la operación es rechazada con el mensaje "Ya existe un producto con el SKU INS-MALTA"

  @UC-CAT-02 @borde @RF-CAT-08
  Escenario: El mismo SKU en otra empresa sí se permite
    Dado que "Brew Lima" tiene el producto con SKU "INS-MALTA"
    Cuando creo un producto con SKU "INS-MALTA" en "Cervecería Andina"
    Entonces el producto se crea correctamente

  @UC-CAT-02 @borde @RF-CAT-09
  Escenario: Campos inmutables después de tener movimientos
    Dado que el producto "INS-MALTA" tiene movimientos de inventario
    Cuando intento cambiar su SKU, tipo o unidad
    Entonces la operación es rechazada con el mensaje "No se puede modificar SKU, tipo o unidad de un producto con movimientos"
    Pero puedo cambiar su nombre, categoría y stock mínimo

  @UC-CAT-02 @borde @RF-CAT-10
  Escenario: Límite de productos del plan
    Dado que el plan de la empresa permite 50 productos activos
    Y la empresa tiene 50 productos activos
    Cuando creo un producto nuevo
    Entonces la operación es rechazada con el mensaje "Tu plan permite hasta 50 productos activos"

  @UC-CAT-01 @RF-CAT-03
  Escenario: Unidad en uso no se elimina
    Dado que la unidad "KG" está asignada a "INS-MALTA"
    Cuando intento eliminar la unidad "KG"
    Entonces la operación es rechazada con el mensaje "La unidad está en uso; puedes desactivarla"

  @UC-CAT-04 @critico @RF-CAT-19
  Escenario: Producto desactivado no se ofrece en operaciones nuevas
    Dado que el producto "INS-LUP-CS" tiene stock 0
    Cuando lo desactivo
    Entonces no aparece al registrar compras ni al editar recetas
    Pero sigue visible en el kardex y en los reportes históricos

  @UC-CAT-04 @borde @RF-CAT-20
  Escenario: No se desactiva un producto con stock
    Dado que el producto "INS-MALTA" tiene stock 25 KG
    Cuando intento desactivarlo
    Entonces la operación es rechazada con el mensaje "El producto tiene stock. Ajusta el stock a cero antes de desactivarlo"

  @UC-CAT-04 @RF-CAT-21
  Escenario: Eliminar producto sin movimientos
    Dado que el producto "ENV-BOT330" no tiene movimientos
    Cuando lo elimino
    Entonces el producto deja de existir

  @UC-CAT-04 @borde @RF-CAT-21
  Escenario: No se elimina un producto con movimientos
    Dado que el producto "INS-MALTA" tiene movimientos de inventario
    Cuando intento eliminarlo
    Entonces la operación es rechazada con el mensaje "El producto tiene historial; solo puede desactivarse"

  @UC-CAT-02 @RN-CAT-06 @critico @RF-CAT-06 @RF-CAT-12 @RF-CAT-13
  Escenario: Crear mercadería de reventa perecible
    Cuando creo el producto "MER-AGUA-500" "Agua sin gas 500 ml" de tipo "MERCADERIA" con:
      | campo          | valor |
      | unidad         | UND   |
      | precio_venta   | 3.00  |
      | controla_lote  | sí    |
      | vida_util_dias | 365   |
    Entonces "MER-AGUA-500" queda activo, comprable y vendible
    Y no requiere presentación ni receta
    Y no paga ISC porque no tiene categoría de ISC

  @UC-CAT-02 @borde @RF-CAT-06 @RF-CAT-12
  Escenario: Mercadería no perecible sin lote
    Cuando creo el producto "MER-POLO-M" "Polo de la marca talla M" de tipo "MERCADERIA" con precio 45.00 y "controla_lote" no
    Entonces "MER-POLO-M" queda activo y vendible sin control de lote

  @UC-CAT-02 @RN-CAT-10 @borde @RF-CAT-26
  Escenario: Mercadería con ISC requiere contenido en litros
    Cuando creo el producto "MER-CERV-TERCERO" de tipo "MERCADERIA" con categoría de ISC "Cerveza" y sin contenido en litros
    Entonces la operación es rechazada con el mensaje "Un producto con ISC por litro requiere el contenido en litros por unidad"

