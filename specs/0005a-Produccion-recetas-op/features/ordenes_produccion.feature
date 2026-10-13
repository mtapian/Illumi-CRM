# language: es
@E05 @E05a @mvp
Característica: Órdenes de producción
  Como maestro cervecero
  Quiero producir cualquier bien con una orden que consume componentes y obtiene un lote
  Para conocer el costo real de cada lote y de cada unidad envasada

  Antecedentes:
    Dado que soy usuario "produccion" de "Cervecería Andina"
    Y el bien que se fabrica "GRA-IPA" en "L" con vida útil 60 días y receta por unidad:
      | componente    | cantidad |
      | INS-MALTA     | 0.2      |
      | INS-MALTA-CAR | 0.02     |
      | INS-LUP-CS    | 3        |
      | INS-LEV-US05  | 0.02     |
    Y el stock en "Principal" con costo promedio:
      | producto      | stock | costo     |
      | INS-MALTA     | 300   | 4.000000  |
      | INS-MALTA-CAR | 15    | 6.000000  |
      | INS-LUP-CS    | 4000  | 0.120000  |
      | INS-LEV-US05  | 12    | 15.000000 |

  @UC-PRD-01 @critico @RF-PRD-36 @RF-PRD-37 @RF-PRD-39
  Escenario: Crear una OP copia la receta y muestra la disponibilidad
    Cuando creo una OP de 500 "GRA-IPA" con su receta y el comentario "Pedido de Bar Central"
    Entonces la OP "OP-000001" queda "Creada" sin movimientos de stock
    Y sus componentes son:
      | componente    | por consumir | disponibilidad |
      | INS-MALTA     | 100.0000     | Disponible     |
      | INS-MALTA-CAR | 10.0000      | Disponible     |
      | INS-LUP-CS    | 1500.0000    | Disponible     |
      | INS-LEV-US05  | 10.0000      | Disponible     |

  @UC-PRD-01 @RF-PRD-38 @RF-PRD-39
  Escenario: Los componentes de la OP se editan sin tocar la receta
    Dado una OP de 500 "GRA-IPA" creada con su receta
    Cuando cambio en la OP "INS-LEV-US05" a 13 y agrego "INS-CLARIF" 1
    Entonces "INS-LEV-US05" aparece "No disponible" en la OP
    Y la receta de "GRA-IPA" no cambia

  @UC-PRD-02 @critico @RF-PRD-41 @RF-PRD-42 @RF-PRD-46
  Escenario: Finalizar una OP consume lo real e ingresa el lote a su costo
    Dado una OP de 500 "GRA-IPA" en proceso con su receta
    Cuando la finalizo con 102 de "INS-MALTA", 425 producidos y costo indirecto 52.00
    Entonces la OP queda "Finalizada"
    Y el stock de "INS-MALTA" es 198
    Y el lote "GRA-IPA-0001" de "GRA-IPA" tiene 425 a costo 2.000000 y vence 60 días después
    Y la merma de "INS-MALTA" en la OP es 2.0000

  @UC-PRD-02 @critico @RF-PRD-41 @RF-PRD-46
  Escenario: El envasado hereda el lote del granel
    Dado el lote "IPA-0020" de "GRA-IPA" con 425 L a costo 2.000000
    Y los bienes que se compran con stock y costo:
      | producto   | stock | costo    |
      | ENV-BOT330 | 2000  | 0.850000 |
      | ENV-TAPA   | 2000  | 0.050000 |
      | ENV-ETQ    | 2000  | 0.200000 |
      | ENV-CAJA24 | 100   | 2.400000 |
    Y el bien que se fabrica "TER-IPA-330" en "UND" con receta por unidad:
      | componente | cantidad |
      | GRA-IPA    | 0.33     |
      | ENV-BOT330 | 1        |
      | ENV-TAPA   | 1        |
      | ENV-ETQ    | 1        |
      | ENV-CAJA24 | 0.0417   |
    Y una OP de 1000 "TER-IPA-330" en proceso con su receta
    Cuando la finalizo con 340 de "GRA-IPA" y 1000 producidos
    Entonces se sugiere el lote "IPA-0020"
    Y el lote "IPA-0020" de "TER-IPA-330" tiene 1000 a costo 1.880080
    Y el lote "IPA-0020" de "GRA-IPA" queda con 85

  @UC-PRD-02 @critico @borde @RF-PRD-09
  Escenario: No se finaliza con componentes insuficientes
    Dado una OP de 500 "GRA-IPA" en proceso con su receta
    Cuando la finalizo con 13 de "INS-LEV-US05" y 425 producidos
    Entonces la operación es rechazada con el mensaje "Stock insuficiente: INS-LEV-US05 faltan 1.0000"
    Y no se registró ningún movimiento de stock

  @UC-PRD-02 @borde @RF-PRD-14
  Escenario: Producir más de lo programado se permite con advertencia
    Dado una OP de 500 "GRA-IPA" en proceso con su receta
    Cuando la finalizo con 510 producidos
    Entonces la OP queda "Finalizada" con la advertencia "Rendimiento mayor a 100 %"

  @UC-PRD-02 @critico @borde @RF-PRD-15
  Escenario: Un lote perdido consume los componentes y registra la pérdida
    Dado una OP de 500 "GRA-IPA" en proceso con su receta
    Cuando la finalizo con 0 producidos y el motivo "Contaminación"
    Entonces la OP queda "Finalizada" sin lote de "GRA-IPA"
    Y el stock de "INS-MALTA" es 200
    Y la OP registra una pérdida de producción de 790.00

  @UC-PRD-02 @borde @RF-PRD-15
  Escenario: Producción 0 sin motivo se rechaza
    Dado una OP de 500 "GRA-IPA" en proceso con su receta
    Cuando la finalizo con 0 producidos
    Entonces la operación es rechazada con el mensaje "Indica el motivo del lote perdido"

  @UC-PRD-02 @borde @RF-PRD-12
  Escenario: Dos finalizaciones simultáneas consumen una sola vez
    Dado una OP de 500 "GRA-IPA" en proceso con su receta
    Cuando dos usuarios la finalizan a la vez con 425 producidos
    Entonces la OP se finaliza una sola vez
    Y el stock de "INS-MALTA" es 200

  @UC-PRD-03 @critico @RF-PRD-16
  Escenario: Anular una OP en proceso no mueve stock
    Dado una OP de 500 "GRA-IPA" en proceso con su receta
    Y que trabajo como usuario "gerente"
    Cuando anulo la OP con el motivo "Se canceló la cocción"
    Entonces la OP queda "Anulada"
    Y el stock de "INS-MALTA" es 300

  @UC-PRD-03 @borde @RF-PRD-18 @RF-PRD-33
  Esquema del escenario: Transiciones no permitidas
    Dado que trabajo como usuario "gerente"
    Y una OP de 500 "GRA-IPA" en estado "<estado>"
    Cuando intento <accion> la OP
    Entonces la operación es rechazada con el mensaje "<mensaje>"

    Ejemplos:
      | estado     | accion    | mensaje                                                      |
      | Finalizada | anular    | La OP está finalizada: corrígela con un ajuste de inventario |
      | Creada     | finalizar | La OP debe estar en proceso para finalizarla                 |
      | Anulada    | editar    | La OP está anulada                                           |

  @UC-PRD-03 @borde @RF-PRD-16
  Escenario: El rol Producción no puede anular
    Dado una OP de 500 "GRA-IPA" creada con su receta
    Cuando intento anular la OP
    Entonces la operación es rechazada con el mensaje "Acceso denegado"

  @UC-PRD-04 @RF-PRD-34
  Escenario: Los costos de la OP se ocultan sin permiso de costos
    Dado una OP de 500 "GRA-IPA" finalizada con 425 producidos
    Y que a mi rol se le quita el permiso "inventario.costo.ver"
    Cuando abro la OP
    Entonces no veo importes en su pestaña "Costos"
