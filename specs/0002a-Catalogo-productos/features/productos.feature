# language: es
@E02 @E02a @mvp
Característica: Gestión de productos: bienes y servicios
  Como responsable de almacén o producción
  Quiero registrar bienes y servicios con lo que se hace con ellos (vender, comprar, fabricar)
  Para que compras, producción y ventas usen un catálogo único

  Antecedentes:
    Dado que soy usuario "gerente" de "Cervecería Andina"
    Y existen las unidades "UND, KG, G, L"

  @UC-CAT-08 @critico @RF-CAT-37 @RF-CAT-38 @RF-CAT-39
  Esquema del escenario: Crear bienes y servicios con sus casillas de gestión
    Cuando creo el <tipo> "<sku>" "<nombre>" en "<unidad>" que "<gestion>" con precio "<precio>"
    Entonces el producto "<sku>" queda activo con stock 0
    Y su gestión es "<gestion>"

    Ejemplos:
      | tipo     | sku          | nombre               | unidad | gestion             | precio |
      | bien     | INS-MALTA    | Malta Pilsen         | KG     | se compra           |        |
      | bien     | ENV-BOT330   | Botella ámbar 330 ml | UND    | se compra           |        |
      | bien     | GRA-IPA      | IPA a granel         | L      | se fabrica          |        |
      | bien     | MER-AGUA-500 | Agua sin gas 500 ml  | UND    | se compra, se vende | 3.00   |
      | servicio | SRV-DELIVERY | Delivery             | SERV   | se vende            | 8.00   |

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

  @UC-CAT-02 @borde @RF-CAT-43
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

  @UC-CAT-08 @critico @RF-CAT-39 @RF-CAT-40
  Escenario: Bien de reventa que se compra y se vende
    Cuando creo el bien "MER-AGUA-500" "Agua sin gas 500 ml" que se compra y se vende con:
      | campo          | valor |
      | unidad         | UND   |
      | precio_venta   | 3.00  |
      | vida_util_dias | 365   |
    Entonces "MER-AGUA-500" queda activo, se compra y se vende
    Y no tiene receta
    Y no paga ISC porque no está afecto a ISC

  @UC-CAT-06 @RF-CAT-04 @RF-CAT-39
  Escenario: La ficha muestra las pestañas de sus casillas
    Dado que existe el producto con SKU "INS-MALTA"
    Cuando abro la ficha de "INS-MALTA"
    Entonces veo las pestañas "General", "Compras" e "Inventario" y no veo "Ventas" ni "Producción"
    Cuando marco que "INS-MALTA" se vende con precio 5.00
    Entonces "INS-MALTA" se vende y veo la pestaña "Ventas"

  @UC-CAT-06 @borde @RF-CAT-43
  Escenario: Con movimientos un bien no pasa a servicio
    Dado que el producto "INS-MALTA" tiene movimientos de inventario
    Cuando intento cambiar su tipo a "SERVICIO"
    Entonces la operación es rechazada con el mensaje "No se puede modificar SKU, tipo o unidad de un producto con movimientos"

  @UC-CAT-06 @RF-CAT-30 @RF-CAT-59
  Escenario: Desglose del precio de un producto con ISC
    Dado el impuesto "ISC 330 ml" de monto fijo 0.8283 desde "2024-07-01"
    Y el bien "TER-IPA-330" que se vende a 12.00 con impuestos de venta "IGV 18%" e "ISC 330 ml"
    Cuando abro la ficha de "TER-IPA-330"
    Entonces veo el desglose "valor 9.34 + ISC 0.83 + IGV 1.83"

  @UC-CAT-06 @borde @RF-CAT-31
  Escenario: Código de barras único por empresa
    Dado que el producto "ENV-BOT330" tiene el código de barras "7751234567890"
    Cuando asigno el código de barras "7751234567890" a "INS-MALTA"
    Entonces la operación es rechazada con el mensaje "El código de barras ya está asignado a ENV-BOT330"

  @UC-CAT-06 @RF-CAT-32
  Escenario: Historial de cambios del producto
    Dado que existe el producto con SKU "INS-MALTA"
    Cuando cambio su nombre a "Malta Pilsen Premium" y su stock mínimo a 30
    Entonces el historial de "INS-MALTA" muestra mi usuario, la fecha y "nombre: INS-MALTA → Malta Pilsen Premium"
    Y muestra "stock_minimo: 0 → 30"

  @UC-CAT-07 @RF-CAT-33 @RF-CAT-36
  Escenario: Crear marcas y verlas en el listado con sus productos
    Cuando creo la marca "Gloria"
    Y asigno la marca "Gloria" a "INS-MALTA"
    Entonces el listado de marcas muestra "Gloria" con 1 producto
    Y buscar "glo" en marcas muestra "Gloria"
    Cuando creo la marca "gloria"
    Entonces la operación es rechazada con el mensaje "Ya existe la marca gloria"

  @UC-CAT-07 @borde @RF-CAT-33 @RF-CAT-34
  Escenario: Una marca en uso no se elimina, se desactiva
    Dado que la marca "Gloria" la usa el producto "INS-MALTA"
    Cuando intento eliminar la marca "Gloria"
    Entonces la operación es rechazada con el mensaje "La marca está en uso; puedes desactivarla"
    Cuando desactivo la marca "Gloria"
    Entonces "INS-MALTA" conserva la marca "Gloria" y la marca ya no se ofrece en productos nuevos

  @UC-CAT-07 @borde @RF-CAT-35
  Escenario: Editar una unidad en uso
    Dado que la unidad "KG" está asignada a "INS-MALTA"
    Cuando edito la unidad "KG" con nombre "Kilo" y abreviatura "KILO"
    Entonces la operación es rechazada con el mensaje "La unidad está en uso: su abreviatura no se puede cambiar"
    Cuando edito la unidad "KG" con nombre "Kilo" y abreviatura "KG"
    Entonces la unidad "KG" se llama "Kilo"

  @UC-CAT-08 @RF-CAT-37 @RF-CAT-38 @RF-CAT-39
  Escenario: Un servicio se vende sin stock
    Cuando creo el servicio "SRV-DELIVERY" "Delivery" que se vende a 8.00
    Entonces "SRV-DELIVERY" no tiene stock, lote ni pestaña Inventario
    Y veo la pestaña "Ventas"

  @UC-CAT-08 @borde @RF-CAT-38
  Escenario: Un producto sin ninguna casilla de gestión se rechaza
    Cuando creo un bien "INS-X" sin marcar se vende, se compra ni se fabrica
    Entonces la operación es rechazada con el mensaje "Marca al menos una opción: se vende, se compra o se fabrica"

  @UC-CAT-08 @RF-CAT-39 @RF-CAT-41
  Escenario: Un bien fabricado usa cualquier producto del catálogo en su receta
    Dado que existen los bienes "GRA-IPA" que se fabrica, "ENV-BOT330" e "INS-MALTA" que se compran
    Cuando creo el bien "TER-IPA-330" que se fabrica y se vende a 12.00 con vida útil 120 días y receta:
      | componente | cantidad |
      | GRA-IPA    | 0.3300   |
      | ENV-BOT330 | 1        |
    Entonces la receta de "TER-IPA-330" tiene 2 componentes
    Y "TER-IPA-330" no puede ser componente de sí mismo

  @UC-CAT-08 @RF-CAT-42
  Escenario: Peso y volumen opcionales en Inventario
    Cuando registro en "INS-MALTA" peso 25 kg y volumen 0.04 m³
    Entonces la pestaña Inventario de "INS-MALTA" muestra peso 25 kg y volumen 0.04 m³

  @UC-CAT-08 @RF-CAT-40
  Escenario: El lote no es un dato del producto; la vida útil solo sugiere el vencimiento
    Dado que existe el producto con SKU "INS-MALTA"
    Cuando abro la ficha de "INS-MALTA"
    Entonces no veo los campos "Controla lote" ni "Prefijo de lote"
    Cuando registro en "INS-MALTA" una vida útil de 180 días
    Entonces un ingreso de "INS-MALTA" el 2026-10-10 sugiere el vencimiento 2027-04-08

  @UC-CAT-08 @RF-CAT-41
  Escenario: La receta es opcional y puede tener un solo componente
    Cuando creo el bien "GRA-IPA" que se fabrica sin receta
    Entonces "GRA-IPA" se crea sin receta
    Cuando le agrego la receta con un componente "INS-MALTA" 0.2000 por litro
    Entonces la receta de "GRA-IPA" tiene 1 componente
