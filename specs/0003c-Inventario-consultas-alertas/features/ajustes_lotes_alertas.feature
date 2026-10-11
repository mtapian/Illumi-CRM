# language: es
@E03 @E03c @mvp
Característica: Ajustes, lotes, almacenes y alertas
  Como encargado de almacén
  Quiero corregir el stock con evidencia y controlar lotes y vencimientos
  Para que el sistema refleje lo que hay físicamente

  Antecedentes:
    Dado que soy usuario "almacen" de "Cervecería Andina"
    Y la fecha de hoy es "2026-11-01"
    Y el bien "TER-IPA-330" que se fabrica y se vende, con stock por lote en "Principal":
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
  Escenario: Stock valorizado por categoría
    Dado que "TER-IPA-330" es de la categoría "Cervezas" con costo promedio 4.000000
    Cuando consulto el stock con el filtro "se fabrica"
    Entonces veo "TER-IPA-330" con stock 178, costo promedio 4.000000 y valor 712.00
    Y su detalle muestra los lotes "IPA-0012", "IPA-0015" e "IPA-0018" en "Principal"
    Y la categoría "Cervezas" suma 712.00

  @UC-INV-02 @borde @RF-INV-04
  Escenario: Sin permiso de costos no se ven costos ni valor
    Dado que soy usuario "ventas" de la misma empresa
    Cuando consulto el stock
    Entonces veo "TER-IPA-330" con stock 178 y sin costo ni valor

  @UC-INV-05 @borde @RF-INV-14
  Escenario: Un producto sin stock mínimo no está en stock bajo
    Dado que "ENV-CHAPA" tiene stock mínimo 0 y stock 0
    Cuando abro el dashboard
    Entonces el widget "Stock bajo" no muestra "ENV-CHAPA"
