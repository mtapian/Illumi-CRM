# language: es
@E03 @E03c @mvp
Característica: Ajustes, lotes, almacenes y alertas
  Como encargado de almacén
  Quiero corregir el stock con evidencia y controlar lotes y vencimientos
  Para que el sistema refleje lo que hay físicamente

  Antecedentes:
    Dado que soy usuario "almacen" de "Cervecería Andina"
    Y la fecha de hoy es "2026-11-01"
    Y el producto terminado "TER-IPA-330" con stock por lote en "Principal":
      | lote      | vence      | cantidad |
      | IPA-0012  | 2026-10-30 | 10       |
      | IPA-0015  | 2026-12-15 | 48       |
      | IPA-0018  | 2027-02-20 | 120      |

  @UC-INV-06 @RF-INV-15
  Escenario: Alerta de lotes por vencer
    Dado que el umbral de alerta de vencimiento es 45 días
    Cuando abro el dashboard
    Entonces el widget "Por vencer" muestra el lote "IPA-0015" con 44 días restantes
    Y muestra el lote "IPA-0012" como "Vencido"
    Y no muestra el lote "IPA-0018"

  @UC-INV-05 @RF-INV-14
  Escenario: Alerta de stock bajo mínimo
    Dado que "ENV-TAPA" tiene stock mínimo 500 y stock 320
    Cuando abro el dashboard
    Entonces el widget "Stock bajo" muestra "ENV-TAPA" con 320 de 500

  @UC-INV-02 @RF-INV-04 @RF-INV-05
  Escenario: Stock valorizado por tipo
    Cuando consulto el stock con filtro tipo "TERMINADO"
    Entonces veo cada presentación con su stock total, el detalle por almacén y lote, el costo promedio y el valor total
