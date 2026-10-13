# language: es
@E01 @E01b @mvp
Característica: Habilitación de módulos y funcionalidades por la plataforma
  Como super admin de la plataforma
  Quiero definir qué módulos y funcionalidades tiene cada plan y cada empresa
  Para comercializar el producto por paquetes y ajustar casos particulares

  Antecedentes:
    Dado que soy super admin de la plataforma
    Y el plan "Emprendedor" incluye las funcionalidades:
      | modulo     | funcionalidad              |
      | CATALOGO   | Productos y presentaciones |
      | INVENTARIO | Stock y kardex             |
      | INVENTARIO | Ajustes de inventario      |
      | COMPRAS    | Compras y proveedores      |
      | VENTAS     | Clientes                   |
      | VENTAS     | Ventas                     |
      | FINANZAS   | Gastos                     |
    Y la empresa "Cervecería Andina" tiene el plan "Emprendedor"

  @UC-TEN-07 @critico @RF-TEN-25 @RF-TEN-26
  Escenario: Agregar una funcionalidad a un plan valida sus dependencias
    Dado el plan "Básico" incluye las funcionalidades:
      | modulo     | funcionalidad              |
      | CATALOGO   | Productos y presentaciones |
    Cuando agrego al plan "Básico" la funcionalidad "Ajustes de inventario"
    Entonces la operación es rechazada con el mensaje "Ajustes de inventario requiere: Stock y kardex"

  @UC-TEN-07 @critico @RF-TEN-27
  Escenario: Cambio en el plan impacta a todas sus empresas
    Dado que 12 empresas tienen el plan "Emprendedor"
    Cuando agrego al plan "Emprendedor" la funcionalidad "Exportación CSV"
    Entonces veo el aviso "Este cambio afecta a 12 empresas" antes de confirmar
    Y al confirmar, "Exportación CSV" queda habilitada para las 12 empresas

  @UC-TEN-08 @critico @RF-TEN-29 @RF-TEN-34
  Escenario: Agregar un módulo a una empresa con vigencia
    Cuando agrego a "Cervecería Andina" el módulo "PRODUCCION" hasta el "2026-12-31" con motivo "Piloto cervecero"
    Entonces "Cervecería Andina" tiene habilitada "Órdenes de producción" con estado "Agregada"
    Y el plan "Emprendedor" no cambia
    Y el registro de actividad guarda la acción, el super admin, la vigencia y el motivo

  @UC-TEN-08 @critico @RF-TEN-30
  Escenario: Vence la vigencia de un ajuste
    Dado que "Cervecería Andina" tiene agregado el módulo "PRODUCCION" hasta el "2026-12-31"
    Cuando llega el "2027-01-01"
    Entonces "Cervecería Andina" deja de tener habilitado el módulo "PRODUCCION"
    Y sus datos de producción se conservan

  @UC-TEN-08 @RF-TEN-28 @RF-TEN-29
  Escenario: Quitar una funcionalidad incluida en el plan solo para una empresa
    Cuando quito a "Cervecería Andina" la funcionalidad "Ajustes de inventario" con motivo "Solicitud del cliente"
    Entonces "Ajustes de inventario" aparece como "Quitada" para "Cervecería Andina"
    Y las demás empresas del plan "Emprendedor" la conservan

  @UC-TEN-08 @borde @RF-TEN-31
  Escenario: No se quita una dependencia de otra funcionalidad habilitada
    Cuando quito a "Cervecería Andina" la funcionalidad "Stock y kardex"
    Entonces la operación es rechazada con el mensaje "No se puede quitar Stock y kardex: la requieren Ajustes de inventario, Compras y proveedores, Ventas"

  @UC-TEN-08 @borde @RF-TEN-29
  Escenario: Ajuste sin motivo es rechazado
    Cuando agrego a "Cervecería Andina" la funcionalidad "Multialmacén" sin motivo
    Entonces la operación es rechazada con el mensaje "El motivo es obligatorio"

  @UC-TEN-08 @borde @RF-TEN-34
  Escenario: CORE no se puede deshabilitar
    Cuando intento quitar a "Cervecería Andina" el módulo "CORE"
    Entonces la operación no está disponible

  @UC-TEN-08 @borde @RF-TEN-32
  Escenario: Advertencia al quitar un módulo con operaciones en curso
    Dado que "Cervecería Andina" tiene agregado el módulo "PRODUCCION"
    Y tiene 2 OP en estado "EN_PROCESO"
    Cuando quito a "Cervecería Andina" el módulo "PRODUCCION"
    Entonces veo la advertencia "La empresa tiene 2 OP en proceso; quedarán sin poder operarse" antes de confirmar

  @UC-TEN-06 @UC-TEN-08 @RF-TEN-23
  Escenario: Al cambiar de plan se conservan los ajustes de la empresa
    Dado que "Cervecería Andina" tiene agregado el módulo "PRODUCCION" sin vigencia
    Cuando cambio a "Cervecería Andina" al plan "Negocio"
    Entonces sus habilitaciones son las del plan "Negocio" más el módulo "PRODUCCION"

  @UC-TEN-08 @RF-TEN-28
  Escenario: Vista de estado de habilitaciones de la empresa
    Dado que "Cervecería Andina" tiene agregado "Multialmacén" y quitado "Ajustes de inventario"
    Cuando abro "Módulos y funcionalidades" de "Cervecería Andina"
    Entonces veo:
      | funcionalidad              | estado              |
      | Stock y kardex             | Incluida en el plan |
      | Ajustes de inventario      | Quitada             |
      | Multialmacén               | Agregada            |
      | Órdenes de producción      | No incluida         |
