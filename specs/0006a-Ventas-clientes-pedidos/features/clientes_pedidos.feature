# language: es
@E06 @E06a @mvp
Característica: Clientes y pedidos
  Como vendedor
  Quiero registrar clientes y sus pedidos y seguir su avance hasta la entrega
  Para producir a pedido y cumplir las fechas comprometidas

  Antecedentes:
    Dado que soy usuario "ventas" de "Cervecería Andina"
    Y la fecha de hoy es "2026-11-10"
    Y el cliente "Bar El Lúpulo" con RUC "20512345671" y canal "B2B"
    Y las presentaciones con stock disponible sin vencer:
      | presentacion | precio_lista | stock |
      | TER-IPA-330  | 12.00        | 48    |
      | TER-IPA-B20  | 380.00       | 0     |
    Y no hay granel disponible de "GRA-IPA"

  @UC-VEN-01 @RF-VEN-01 @RF-VEN-02
  Esquema del escenario: Validación del documento del cliente
    Cuando creo el cliente "<nombre>" con tipo "<tipo>" y número "<numero>"
    Entonces el resultado es "<resultado>"

    Ejemplos:
      | nombre           | tipo | numero      | resultado                   |
      | Ana Quispe       | DNI  | 45871236    | creado                      |
      | Ana Quispe       | DNI  | 4587123     | El DNI debe tener 8 dígitos |
      | Resto Miraflores | RUC  | 20512345670 | El RUC no es válido         |

  @UC-VEN-02 @UC-VEN-03 @critico @RF-VEN-06 @RF-VEN-08 @RF-VEN-09
  Escenario: Confirmar pedido muestra faltantes y propone producir
    Cuando creo un pedido para "Bar El Lúpulo" con entrega el "2026-12-05":
      | presentacion | cantidad | precio |
      | TER-IPA-330  | 96       | 11.00  |
      | TER-IPA-B20  | 4        | 380.00 |
    Y confirmo el pedido
    Entonces el pedido "P-000001" queda "CONFIRMADO" con total 2576.00
    Y muestra los faltantes:
      | presentacion | pedido | disponible | faltante |
      | TER-IPA-330  | 96     | 48         | 48       |
      | TER-IPA-B20  | 4      | 0          | 4        |
    Y ofrece planificar producción de "GRA-IPA" por 95.84 L

  @UC-VEN-03 @borde @RF-VEN-11
  Escenario: Pedido confirmado no se edita
    Dado el pedido "P-000001" en estado "CONFIRMADO"
    Cuando intento cambiar el precio de una línea
    Entonces la operación es rechazada con el mensaje "El pedido está confirmado; cancélalo y crea uno nuevo para cambiarlo"

  @UC-VEN-04 @critico @RF-VEN-12 @RF-VEN-13 @RF-PRD-11 @RF-PRD-27
  Escenario: El pedido avanza con la producción vinculada
    Dado el pedido "P-000001" en estado "CONFIRMADO" vinculado a la OP "OP-000020"
    Cuando se inicia "OP-000020"
    Entonces "P-000001" pasa a "EN_PRODUCCION"
    Cuando se envasa "OP-000020" y el stock disponible cubre todas las líneas de "P-000001"
    Entonces "P-000001" pasa a "LISTO"

  @UC-VEN-04 @borde @RF-VEN-13
  Escenario: Envasado que no cubre el pedido completo
    Dado el pedido "P-000001" en estado "EN_PRODUCCION" vinculado a "OP-000020"
    Cuando se envasa "OP-000020" solo en botellas y no hay stock de "TER-IPA-B20"
    Entonces "P-000001" sigue "EN_PRODUCCION"

  @UC-VEN-04 @RF-VEN-15
  Escenario: Alerta de pedidos atrasados
    Dado el pedido "P-000002" con entrega el "2026-11-08" en estado "CONFIRMADO"
    Cuando abro el tablero de pedidos
    Entonces "P-000002" aparece marcado como "Atrasado 2 días"

  @UC-VEN-07 @RF-VEN-37 @RF-VEN-42
  Escenario: Cancelar pedido en producción desvincula la OP
    Dado el pedido "P-000001" en estado "EN_PRODUCCION" vinculado a "OP-000020"
    Cuando cancelo "P-000001" con motivo "Cliente cerró el local"
    Entonces "P-000001" queda "CANCELADO"
    Y "OP-000020" sigue en su estado y ya no está vinculada a "P-000001"
    Y veo el aviso "La OP-000020 continúa; su producción queda disponible para otros pedidos"

  @UC-VEN-07 @borde @RF-VEN-16 @RF-VEN-37
  Escenario: Un pedido entregado no se cancela
    Dado el pedido "P-000003" en estado "ENTREGADO"
    Cuando intento cancelarlo
    Entonces la operación es rechazada con el mensaje "Un pedido entregado no se puede cancelar; anula la venta"

  @UC-VEN-03 @borde @RF-VEN-10
  Escenario: Faltante de mercadería se compra, no se produce
    Dado "MER-AGUA-500" con stock disponible 0
    Cuando confirmo un pedido para "Bar El Lúpulo" con 24 "MER-AGUA-500" a 3.00
    Entonces muestra el faltante de 24 "MER-AGUA-500" como "por comprar"
    Y no ofrece planificar producción

  @UC-VEN-04 @borde @RF-VEN-41 @RF-PRD-32
  Escenario: Pedido en producción sin OP activa y sin stock suficiente vuelve a CONFIRMADO
    Dado el pedido "P-000001" "EN_PRODUCCION" de 96 unidades de "TER-IPA-330" vinculado solo a "OP-000020"
    Y el envasado de "OP-000020" dejó 60 unidades disponibles de "TER-IPA-330"
    Cuando "OP-000020" se cierra
    Entonces "P-000001" vuelve a "CONFIRMADO"
    Y muestra un faltante de 36 unidades de "TER-IPA-330"
