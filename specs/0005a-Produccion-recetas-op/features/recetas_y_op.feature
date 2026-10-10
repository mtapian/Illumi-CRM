# language: es
@E05 @E05a @mvp
Característica: Recetas y órdenes de producción
  Como maestro cervecero
  Quiero planificar, iniciar y terminar órdenes de producción desde recetas
  Para conocer el costo real por litro de cada lote

  Antecedentes:
    Dado que soy usuario "produccion" de "Cervecería Andina"
    Y el granel "GRA-IPA" con prefijo de lote "IPA" y vida útil 60 días
    Y el stock en "Principal" con costo promedio:
      | producto      | stock | unidad | costo    |
      | INS-MALTA     | 300   | KG     | 4.000000 |
      | INS-MALTA-CAR | 15    | KG     | 6.000000 |
      | INS-LUP-CS    | 4000  | G      | 0.120000 |
      | INS-LEV-US05  | 12    | UND    | 15.000000 |
    Y la receta "IPA" versión 1 de "GRA-IPA" con volumen base 500 L:
      | insumo        | cantidad |
      | INS-MALTA     | 100      |
      | INS-MALTA-CAR | 10       |
      | INS-LUP-CS    | 1500     |
      | INS-LEV-US05  | 10       |

  @UC-PRD-01 @critico @RF-PRD-02 @RF-PRD-03
  Escenario: Editar una receta usada crea una nueva versión
    Dado una OP creada con la receta "IPA" versión 1
    Cuando cambio la cantidad de "INS-LUP-CS" de la receta "IPA" a 1800
    Entonces existe la receta "IPA" versión 2 activa con 1800 G de "INS-LUP-CS"
    Y la OP existente sigue referenciando la versión 1

  @UC-PRD-01 @borde @RF-PRD-01
  Escenario: La receta solo admite insumos
    Cuando agrego el envase "ENV-BOT330" a la receta "IPA"
    Entonces la operación es rechazada con el mensaje "La receta solo admite productos tipo INSUMO"

  @UC-PRD-02 @critico @RF-PRD-04 @RF-PRD-05 @RF-PRD-06
  Escenario: Planificar una OP escala los insumos y advierte faltantes
    Cuando planifico una OP de la receta "IPA" por 750 L
    Entonces la OP "OP-000001" queda "PLANIFICADA" con insumos teóricos:
      | insumo        | teorico | disponible | faltante |
      | INS-MALTA     | 150     | 300        | 0        |
      | INS-MALTA-CAR | 15      | 15         | 0        |
      | INS-LUP-CS    | 2250    | 4000       | 0        |
      | INS-LEV-US05  | 15      | 12         | 3        |
    Y veo la advertencia "Faltan insumos para iniciar: INS-LEV-US05 (3 UND)"
    Y el stock no cambia

  @UC-PRD-03 @critico @RF-PRD-08
  Escenario: Iniciar OP consume los insumos reales al costo promedio
    Dado la OP "OP-000020" planificada de la receta "IPA" por 500 L
    Cuando inicio "OP-000020" con consumos reales:
      | insumo        | real |
      | INS-MALTA     | 102  |
      | INS-MALTA-CAR | 10   |
      | INS-LUP-CS    | 1500 |
      | INS-LEV-US05  | 10   |
    Entonces "OP-000020" queda "EN_PROCESO" con costo de insumos 798.00
    Y el kardex registra salidas "CONSUMO_OP" que referencian "OP-000020"
    Y el stock de "INS-MALTA" es 198 KG

  @UC-PRD-03 @critico @borde @RF-PRD-09
  Escenario: No se inicia una OP con insumos insuficientes
    Dado la OP "OP-000021" planificada de la receta "IPA" por 750 L
    Cuando intento iniciar "OP-000021" con las cantidades teóricas
    Entonces la operación es rechazada con el mensaje "Stock insuficiente: INS-LEV-US05 requiere 15 y hay 12"
    Y no se registra ningún consumo

  @UC-PRD-03 @RF-PRD-10
  Escenario: Consumo adicional durante el proceso (dry hopping)
    Dado la OP "OP-000020" en estado "EN_PROCESO" con costo de insumos 798.00
    Cuando registro un consumo adicional de 500 G de "INS-LUP-CS" en "OP-000020"
    Entonces el costo de insumos de "OP-000020" es 858.00

  @UC-PRD-04 @critico @RF-PRD-13
  Escenario: Terminar OP crea el lote de granel con su costo por litro
    Dado la OP "OP-000020" en estado "EN_PROCESO" con costo de insumos 798.00
    Y el último correlativo de lote de "GRA-IPA" es 19
    Cuando termino "OP-000020" el "2026-11-20" con 425 L reales y costo indirecto 52.00 en "Principal"
    Entonces "OP-000020" queda "TERMINADA" con:
      | costo_total | costo_por_litro | rendimiento |
      | 850.00      | 2.000000        | 85.00 %     |
    Y existe el lote "IPA-0020" de "GRA-IPA" con 425 L que vence el "2027-01-19"
    Y el kardex registra una entrada "PRODUCCION" de 425 L de "GRA-IPA" a costo 2.000000

  @UC-PRD-04 @borde @RF-PRD-14
  Escenario: Rendimiento mayor al 100 % se permite con advertencia
    Dado la OP "OP-000020" en estado "EN_PROCESO" planificada por 500 L
    Cuando termino "OP-000020" con 520 L reales
    Entonces "OP-000020" queda "TERMINADA" con rendimiento 104.00 %
    Y veo la advertencia "Los litros reales superan lo planificado"

  @UC-PRD-04 @borde @pendiente-q10 @RF-PRD-15
  Escenario: Lote perdido se termina con 0 litros
    Dado la OP "OP-000020" en estado "EN_PROCESO" con costo de insumos 798.00
    Cuando termino "OP-000020" con 0 L y motivo "Contaminación bacteriana"
    Entonces "OP-000020" queda "CERRADA" sin lote
    Y su costo de 798.00 se reporta como pérdida de producción del período

  @UC-PRD-05 @critico @RF-PRD-17
  Escenario: Anular una OP en proceso revierte los consumos
    Dado la OP "OP-000020" en estado "EN_PROCESO" que consumió 102 KG de "INS-MALTA" a 4.000000
    Cuando un usuario "gerente" anula "OP-000020" con motivo "Error de receta, insumos no usados"
    Entonces se registra una entrada "ANULACION" de 102 KG de "INS-MALTA" a costo 4.000000
    Y "OP-000020" queda "ANULADA"

  @UC-PRD-05 @borde @RF-PRD-18 @RF-PRD-33
  Esquema del escenario: Transiciones de estado inválidas
    Dado una OP en estado "<estado>"
    Cuando intento "<accion>"
    Entonces la operación es rechazada con el mensaje "<mensaje>"

    Ejemplos:
      | estado      | accion   | mensaje                                         |
      | TERMINADA   | anular   | Una OP terminada no se puede anular             |
      | CERRADA     | anular   | Una OP terminada no se puede anular             |
      | PLANIFICADA | terminar | La OP debe estar en proceso para terminarla     |
      | ANULADA     | iniciar  | La OP está anulada                              |

  @UC-PRD-05 @borde @RF-PRD-16
  Escenario: Rol producción no puede anular
    Dado la OP "OP-000020" en estado "PLANIFICADA"
    Cuando un usuario "produccion" intenta anular "OP-000020"
    Entonces la operación es denegada

  @UC-PRD-05 @borde @RF-PRD-19 @RF-VEN-42
  Escenario: Anular una OP devuelve a CONFIRMADO solo los pedidos que dependían de ella
    Dado la OP "OP-000020" "EN_PROCESO" vinculada a los pedidos "P-000001" y "P-000002"
    Y "P-000001" está "EN_PRODUCCION" sin otra OP vinculada
    Y "P-000002" está "EN_PRODUCCION" y también vinculado a "OP-000021" "EN_PROCESO"
    Cuando un usuario "gerente" anula "OP-000020" con motivo "Error de planificación"
    Entonces "P-000001" vuelve a "CONFIRMADO"
    Y "P-000002" sigue "EN_PRODUCCION"
