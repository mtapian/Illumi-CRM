# language: es
@E01 @E01d @mvp
Característica: Auditoría de cambios de acceso
  Como administrador de una empresa
  Quiero ver quién cambió roles, permisos y usuarios
  Para auditar los accesos

  Antecedentes:
    Dado la empresa "Cervecería Andina" con las funcionalidades habilitadas:
      | modulo     | funcionalidad              |
      | CATALOGO   | Productos y presentaciones |
      | INVENTARIO | Stock y kardex             |
      | INVENTARIO | Ajustes de inventario      |
      | VENTAS     | Clientes                   |
      | VENTAS     | Pedidos                    |
      | VENTAS     | Ventas                     |
    Y la funcionalidad "Órdenes de producción" no está habilitada para "Cervecería Andina"
    Y "lucia@andina.pe" tiene el rol "Administrador"

  @UC-TEN-10 @RF-TEN-43 @RF-TEN-44
  Escenario: Auditoría de cambios de acceso
    Dado que "lucia@andina.pe" quitó "ventas.venta.anular" del rol "Gerente" el "2026-11-15"
    Cuando consulto la auditoría de accesos
    Entonces veo el cambio con autor "lucia@andina.pe", fecha, rol "Gerente", antes "incluido" y después "quitado"
