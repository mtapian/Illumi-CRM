# language: es
@E08 @E08a @mvp
Característica: Gastos operativos y estado de resultados
  Como dueño de la cervecera
  Quiero ver la utilidad bruta y operativa de un período
  Para saber cuánto gano realmente

  Antecedentes:
    Dado que soy usuario "admin" de "Cervecería Andina" con IGV 18 %

  @UC-FIN-01 @critico @RF-FIN-01
  Esquema del escenario: El gasto del período excluye el IGV solo con factura
    Cuando registro un gasto de "<categoria>" con documento "<documento>", base <base> e IGV <igv>
    Entonces el gasto del período es <gasto>

    Ejemplos:
      | categoria | documento     | base   | igv   | gasto  |
      | Alquiler  | FACTURA       | 300.00 | 54.00 | 300.00 |
      | Servicios | BOLETA        | 118.00 | 0.00  | 118.00 |
      | Planilla  | SIN_DOCUMENTO | 200.00 | 0.00  | 200.00 |

  @UC-FIN-01 @borde @RF-FIN-02
  Escenario: Gasto con fecha futura
    Cuando registro un gasto con fecha de mañana
    Entonces la operación es rechazada con el mensaje "La fecha del gasto no puede ser futura"

  @UC-FIN-02 @RF-FIN-05
  Escenario: Anular un gasto
    Dado el gasto de "Alquiler" de 300.00 del "2026-11-01"
    Cuando un usuario "gerente" lo anula el "2026-11-10" con motivo "Duplicado"
    Entonces los gastos operativos de noviembre bajan en 300.00

  @UC-FIN-02 @RN-FIN-03 @borde @RF-FIN-05
  Escenario: Un gasto anulado en otro mes resta en el mes de la anulación
    Dado el gasto de "Alquiler" de 300.00 del "2026-10-01"
    Cuando un usuario "gerente" lo anula el "2026-11-05" con motivo "Duplicado"
    Entonces los gastos operativos de octubre siguen incluyendo 300.00
    Y los gastos operativos de noviembre restan 300.00

  @UC-FIN-01 @borde @RF-FIN-04
  Escenario: Advertencia por posible doble conteo con el costo indirecto de la OP
    Dado la categoría "Gas de cocción" marcada como "de planta"
    Cuando registro un gasto de "Gas de cocción"
    Entonces veo la advertencia "Si ya cargaste este costo como costo indirecto en una OP, no lo registres también como gasto"
