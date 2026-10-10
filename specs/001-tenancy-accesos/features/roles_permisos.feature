# language: es
@E01 @mvp
Característica: Roles y permisos administrados por la empresa
  Como administrador de una empresa
  Quiero crear roles con los permisos que mi plan habilita y asignarlos a mis usuarios
  Para que cada persona haga solo lo que le corresponde

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

  @UC-TEN-01 @UC-TEN-09 @critico @RF-TEN-01
  Escenario: Roles iniciales al registrar la empresa
    Cuando se registra la empresa "Cervecería Andina"
    Entonces existen los roles "Administrador" (sistema), "Gerente", "Producción", "Almacén" y "Ventas"
    Y los roles editables solo contienen permisos de funcionalidades habilitadas

  @UC-TEN-09 @critico @RF-TEN-35
  Escenario: Crear un rol propio con permisos habilitados
    Cuando "lucia@andina.pe" crea el rol "Vendedor taproom" con los permisos:
      | permiso                 |
      | ventas.cliente.ver      |
      | ventas.venta.registrar  |
      | ventas.venta.ver        |
      | inventario.stock.ver    |
    Entonces el rol "Vendedor taproom" queda activo con 4 permisos

  @UC-TEN-09 @critico @RF-TEN-35
  Escenario: El editor de roles bloquea lo no habilitado
    Cuando "lucia@andina.pe" abre el editor del rol "Gerente"
    Entonces la funcionalidad "Órdenes de producción" aparece bloqueada con la etiqueta "No incluido en tu plan"

  @UC-TEN-09 @critico @borde @RF-TEN-36
  Escenario: El servidor rechaza permisos no habilitados
    Cuando "lucia@andina.pe" envía el rol "Gerente" con el permiso "produccion.op.ejecutar" manipulando el formulario
    Entonces la operación es rechazada con el mensaje "El permiso produccion.op.ejecutar no está incluido en tu plan"

  @UC-TEN-03 @UC-TEN-09 @critico @RF-TEN-10
  Escenario: Permisos efectivos con varios roles
    Dado el rol "Vendedor taproom" con "ventas.venta.registrar"
    Y el rol "Inventarista" con "inventario.ajuste.registrar"
    Cuando "lucia@andina.pe" asigna ambos roles a "ana@andina.pe"
    Entonces "ana@andina.pe" puede registrar una venta
    Y "ana@andina.pe" puede registrar un ajuste de inventario
    Pero "ana@andina.pe" no puede anular una venta

  @UC-TEN-09 @critico @RF-TEN-33 @RF-TEN-39 @RF-TEN-40
  Escenario: Los permisos dejan de ser efectivos si la plataforma quita la funcionalidad
    Dado el rol "Inventarista" con "inventario.ajuste.registrar" asignado a "rosa@andina.pe"
    Cuando el super admin quita a "Cervecería Andina" la funcionalidad "Ajustes de inventario"
    Entonces "rosa@andina.pe" no puede registrar ajustes desde su siguiente acción
    Y el menú de "rosa@andina.pe" ya no muestra "Ajustes"
    Y el rol "Inventarista" conserva el permiso marcado como "No disponible en tu plan"
    Cuando el super admin vuelve a agregar "Ajustes de inventario"
    Entonces "rosa@andina.pe" vuelve a poder registrar ajustes sin que nadie edite su rol

  @UC-TEN-09 @critico @RF-TEN-37
  Escenario: El Administrador recibe automáticamente lo que se habilita después
    Cuando el super admin agrega a "Cervecería Andina" la funcionalidad "Órdenes de producción"
    Entonces "lucia@andina.pe" puede planificar una OP sin cambios en sus roles

  @UC-TEN-09 @borde @RF-TEN-37
  Escenario: El rol Administrador no se edita
    Cuando "lucia@andina.pe" intenta editar o eliminar el rol "Administrador"
    Entonces la operación no está disponible

  @UC-TEN-09 @borde @RF-TEN-38
  Escenario: Rol con usuarios se desactiva en vez de eliminarse
    Dado el rol "Vendedor taproom" asignado a 2 usuarios
    Cuando "lucia@andina.pe" intenta eliminar "Vendedor taproom"
    Entonces la operación es rechazada con el mensaje "El rol tiene 2 usuarios; puedes desactivarlo"
    Cuando lo desactiva
    Entonces esos usuarios pierden los permisos del rol desde su siguiente acción

  @UC-TEN-03 @borde @RF-TEN-41
  Escenario: Usuario sin permisos efectivos
    Dado el rol propio "Solo cocina" con únicamente los permisos "produccion.op.ver" y "produccion.op.ejecutar"
    Y que "pedro@andina.pe" solo tiene el rol "Solo cocina" y la empresa no tiene habilitado PRODUCCION
    Cuando "pedro@andina.pe" inicia sesión
    Entonces ve el mensaje "No tienes módulos asignados. Contacta al administrador de tu empresa"

  @UC-TEN-03 @RF-TEN-14
  Escenario: Ver los permisos efectivos de un usuario
    Dado "ana@andina.pe" con los roles "Vendedor taproom" e "Inventarista"
    Cuando "lucia@andina.pe" abre la ficha de "ana@andina.pe"
    Entonces ve sus permisos efectivos agrupados por módulo con el rol de origen de cada uno

  @UC-TEN-09 @borde @RF-TEN-51
  Escenario: Ocultar costos a un rol
    Dado el rol "Vendedor taproom" sin "inventario.costo.ver" asignado a "ana@andina.pe"
    Cuando "ana@andina.pe" consulta el stock
    Entonces ve cantidades por producto y lote
    Pero no ve costo promedio ni valorización

  @UC-TEN-09 @RN-TEN-12 @critico @RF-TEN-49
  Esquema del escenario: Autorización en el servidor por permiso
    Dado el usuario "ana@andina.pe" sin el permiso "<permiso>"
    Cuando invoca directamente la acción "<accion>"
    Entonces recibe "Acceso denegado"
    Y la acción no se ejecuta

    Ejemplos:
      | permiso                     | accion                      |
      | ventas.venta.anular         | anular una venta            |
      | compras.compra.registrar    | registrar una compra        |
      | finanzas.resultados.ver     | ver el estado de resultados |
      | core.usuario.gestionar      | crear un usuario            |
      | api.token.gestionar         | generar un token de API     |

  @UC-TEN-10 @RF-TEN-43 @RF-TEN-44
  Escenario: Auditoría de cambios de acceso
    Dado que "lucia@andina.pe" quitó "ventas.venta.anular" del rol "Gerente" el "2026-11-15"
    Cuando consulto la auditoría de accesos
    Entonces veo el cambio con autor "lucia@andina.pe", fecha, rol "Gerente", antes "incluido" y después "quitado"
