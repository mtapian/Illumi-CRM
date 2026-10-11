# language: es
@E02 @E02d @mvp @borrador
Característica: Proveedores y proveedores del producto
  Como encargado de almacén
  Quiero registrar a mis proveedores y ver a quién le compro cada producto
  Para reponer a tiempo y al precio esperado

  Antecedentes:
    Dado que soy usuario "almacen" de "Cervecería Andina"
    Y existe el producto con SKU "INS-MALTA"

  @UC-COM-01 @critico @RF-COM-01
  Escenario: Registrar un proveedor
    Cuando registro el proveedor "Maltería del Sur" con RUC "20512345671"
    Entonces el proveedor "Maltería del Sur" queda activo

  @UC-COM-01 @borde @RF-COM-01
  Esquema del escenario: Documento inválido o duplicado
    Dado el proveedor "Maltería del Sur" con RUC "20512345671"
    Cuando registro el proveedor "Otro" con <tipo> "<numero>"
    Entonces la operación es rechazada con el mensaje "<mensaje>"

    Ejemplos:
      | tipo | numero      | mensaje                                        |
      | RUC  | 20512345672 | El RUC no es válido                            |
      | DNI  | 1234567     | El DNI debe tener 8 dígitos                    |
      | RUC  | 20512345671 | Ya existe un proveedor con el RUC 20512345671  |

  @UC-COM-01 @RF-COM-02
  Escenario: Proveedor con compras se desactiva en vez de eliminarse
    Dado el proveedor "Maltería del Sur" con RUC "20512345671"
    Y que "Maltería del Sur" tiene compras
    Cuando intento eliminar "Maltería del Sur"
    Entonces la operación es rechazada con el mensaje "El proveedor tiene compras; puedes desactivarlo"

  @UC-COM-08 @critico @RF-COM-21 @RF-COM-22
  Escenario: Asociar un proveedor a un insumo
    Dado el proveedor "Maltería del Sur" con RUC "20512345671"
    Cuando asocio "Maltería del Sur" a "INS-MALTA" con precio 4.80 y plazo 3 días
    Entonces la pestaña "Compras" de "INS-MALTA" muestra "Maltería del Sur" con precio 4.80 y plazo 3 días
    Cuando lo vuelvo a asociar con precio 5.10
    Entonces "INS-MALTA" tiene un solo registro de "Maltería del Sur" con precio 5.10

  @UC-COM-08 @borde @RF-COM-03 @RF-COM-21
  Escenario: Un proveedor desactivado no se asocia
    Dado el proveedor "Maltería del Sur" con RUC "20512345671"
    Y que "Maltería del Sur" está desactivado
    Cuando asocio "Maltería del Sur" a "INS-MALTA" con precio 4.80 y plazo 3 días
    Entonces la operación es rechazada con el mensaje "El proveedor está desactivado"

  @UC-COM-08 @borde @RF-COM-22
  Escenario: Un producto que no se compra no tiene pestaña Compras
    Dado existe el granel "GRA-IPA" (IPA a granel)
    Cuando abro la ficha de "GRA-IPA"
    Entonces no veo la pestaña "Compras"
