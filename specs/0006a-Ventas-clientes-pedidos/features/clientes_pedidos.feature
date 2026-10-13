# language: es
@E06 @E06a @mvp
Característica: Clientes y pedidos
  Como vendedor
  Quiero registrar clientes y sus pedidos y ver si tengo stock para entregarlos
  Para cumplir las fechas comprometidas

  Antecedentes:
    Dado que soy usuario "ventas" de "Cervecería Andina"
    Y el cliente "Bar El Lúpulo" con RUC "20512345671" y canal "B2B"
    Y los productos que se venden con stock sin vencer:
      | producto    | precio | stock |
      | TER-IPA-330 | 12.00  | 48    |
      | TER-IPA-20L | 380.00 | 0     |

  @UC-VEN-01 @RF-VEN-01 @RF-VEN-02
  Esquema del escenario: Validación del documento y los datos del cliente
    Cuando creo el cliente "<nombre>" con tipo "<tipo>", número "<numero>" y email "<email>"
    Entonces el resultado es "<resultado>"

    Ejemplos:
      | nombre           | tipo    | numero      | email          | resultado                                  |
      | Ana Quispe       | DNI     | 45871236    | ana@correo.pe  | creado                                     |
      | Ana Quispe       | DNI     | 4587123     |                | El DNI debe tener 8 dígitos                |
      | Resto Miraflores | RUC     | 20512345670 |                | El RUC no es válido                        |
      | Turista          | SD      | 123         |                | Sin documento no lleva número              |
      | Bar Norte        | RUC     | 20100066603 | no-es-un-email | El email no es válido                      |
      | John Smith       | PAS     | X1234567    |                | creado                                     |

  @UC-VEN-01 @borde @RF-VEN-01
  Escenario: El documento no se repite en la empresa
    Cuando creo el cliente "Otro bar" con tipo "RUC", número "20512345671" y email ""
    Entonces el resultado es "Ya existe un cliente con RUC 20512345671"

  @UC-VEN-01 @RF-VEN-03 @RF-VEN-05
  Escenario: Clientes varios existe y no se desactiva
    Entonces la empresa tiene el cliente "Clientes varios" sin documento
    Cuando intento desactivar el cliente "Clientes varios"
    Entonces el resultado es "Clientes varios no se desactiva"

  @UC-VEN-01 @borde @RF-VEN-05 @RF-VEN-44
  Escenario: Un cliente se desactiva, no se elimina, y desactivado no se ofrece
    Dado un pedido de "Bar El Lúpulo" con 24 "TER-IPA-330"
    Cuando desactivo el cliente "Bar El Lúpulo"
    Entonces "Bar El Lúpulo" no se ofrece en un pedido nuevo
    Y el pedido de "Bar El Lúpulo" conserva su cliente

  @UC-VEN-01 @UC-VEN-02 @critico @RF-VEN-50
  Escenario: Buscar el cliente por nombre o documento y registrarlo al vuelo
    Cuando busco el cliente "lúpulo" en un pedido nuevo
    Entonces encuentro "Bar El Lúpulo"
    Cuando busco el cliente "20512345671" en un pedido nuevo
    Entonces encuentro "Bar El Lúpulo"
    Cuando busco el cliente "45871236" en un pedido nuevo
    Entonces no encuentro clientes
    Cuando registro al vuelo el cliente "Ana Quispe" con DNI "45871236" y teléfono "987654321"
    Entonces el pedido nuevo tiene elegido a "Ana Quispe"

  @UC-VEN-02 @UC-VEN-04 @critico @RF-VEN-06 @RF-VEN-45 @RF-VEN-48
  Escenario: Un pedido muestra el stock disponible, el faltante y el quiebre de stock
    Cuando creo un pedido de "Bar El Lúpulo" para el "2026-11-15" con:
      | producto    | cantidad |
      | TER-IPA-330 | 60       |
      | TER-IPA-20L | 2        |
    Entonces el pedido "P-000001" queda "Creado" con total 1480.00
    Y sus líneas muestran:
      | producto    | precio | disponible | faltante | alerta           |
      | TER-IPA-330 | 12.00  | 48         | 12       | Quiebre de stock |
      | TER-IPA-20L | 380.00 | 0          | 2        | Quiebre de stock |

  @UC-VEN-03 @critico @borde @RF-VEN-08
  Escenario: No se aprueba un pedido con quiebre de stock
    Dado un pedido de "Bar El Lúpulo" con 60 "TER-IPA-330"
    Cuando apruebo el pedido
    Entonces el resultado es "Stock insuficiente: TER-IPA-330 faltan 12.0000"
    Y el pedido queda "Creado"

  @UC-VEN-03 @critico @RF-VEN-08 @RF-VEN-11
  Escenario: Aprobar fija las líneas del pedido
    Dado un pedido de "Bar El Lúpulo" con 24 "TER-IPA-330"
    Cuando apruebo el pedido
    Entonces el pedido queda "Aprobado"
    Cuando intento cambiar la cantidad de "TER-IPA-330" a 30
    Entonces el resultado es "El pedido está aprobado: cancélalo y crea otro para cambiar sus líneas"

  @UC-VEN-04 @RF-VEN-15 @RF-VEN-46
  Escenario: Listado con atrasados, quiebre de stock y listos para facturar
    Dado la fecha de hoy es "2026-11-20"
    Y un pedido aprobado de "Bar El Lúpulo" para el "2026-11-15" con 24 "TER-IPA-330"
    Y un pedido de "Bar El Lúpulo" para el "2026-11-25" con 1 "TER-IPA-20L"
    Cuando abro el listado de pedidos
    Entonces veo los indicadores:
      | pedido   | indicadores      |
      | P-000001 | Atrasado         |
      | P-000002 | Quiebre de stock |

  @UC-VEN-04 @RF-VEN-47
  Escenario: Aviso de pedidos con quiebre de stock en el inicio
    Dado un pedido de "Bar El Lúpulo" para el "2026-11-25" con 1 "TER-IPA-20L"
    Cuando abro el inicio
    Entonces veo la alerta "1 pedido con quiebre de stock"
    Y la alerta lleva al listado de pedidos filtrado por "solo con quiebre de stock"

  @UC-VEN-04 @RF-VEN-46
  Escenario: Vista kanban con los mismos pedidos y filtros
    Dado un pedido aprobado de "Bar El Lúpulo" para el "2026-11-15" con 24 "TER-IPA-330"
    Y un pedido de "Bar El Lúpulo" para el "2026-11-25" con 1 "TER-IPA-20L"
    Y un pedido de "Bar El Lúpulo" con 6 "TER-IPA-330"
    Cuando abro los pedidos en la vista "Kanban" con el filtro "solo con quiebre de stock"
    Entonces la columna "Creado" tiene "P-000002"
    Y ninguna columna tiene "P-000001" ni "P-000003"

  @UC-VEN-05 @RF-VEN-37 @RF-VEN-16
  Escenario: Cancelar un pedido exige motivo y permiso
    Dado un pedido de "Bar El Lúpulo" con 24 "TER-IPA-330"
    Y que trabajo como usuario "produccion"
    Cuando intento cancelar el pedido
    Entonces el resultado es "Acceso denegado"
    Dado que trabajo como usuario "ventas"
    Cuando cancelo el pedido con el motivo "El cliente desistió"
    Entonces el pedido queda "Cancelado"
