# language: es
@E01 @E01c @mvp
Característica: Usuarios, plantillas de rol y aislamiento
  Como administrador de una empresa
  Quiero controlar quién accede y qué puede hacer
  Para proteger la información de mi negocio

  Antecedentes:
    Dado la empresa "Cervecería Andina" con plan que permite 10 usuarios
    Y la empresa "Brew Lima" con datos propios
    Y el usuario "lucia@andina.pe" con el rol "Administrador" de "Cervecería Andina"
    Y "Cervecería Andina" tiene habilitados todos los módulos

  @UC-TEN-03 @critico @RF-TEN-10
  Escenario: Administrador crea un usuario con un rol
    Cuando "lucia@andina.pe" crea el usuario "mario@andina.pe" con el rol "Producción"
    Entonces "mario@andina.pe" puede iniciar sesión en "Cervecería Andina"
    Y "mario@andina.pe" puede acceder al módulo de producción
    Pero "mario@andina.pe" no puede acceder al módulo de ventas

  @UC-TEN-03 @borde @RF-TEN-11
  Escenario: Límite de usuarios del plan
    Dado que el plan de "Cervecería Andina" se cambia a uno que permite 3 usuarios
    Y "Cervecería Andina" tiene 3 usuarios activos
    Cuando "lucia@andina.pe" intenta crear el usuario "nuevo@andina.pe"
    Entonces la operación es rechazada con el mensaje "Tu plan permite hasta 3 usuarios activos"

  @UC-TEN-03 @borde @RF-TEN-12
  Escenario: El último administrador no puede desactivarse
    Dado que "lucia@andina.pe" es el único usuario activo con el rol "Administrador"
    Cuando "lucia@andina.pe" intenta desactivarse o quitarse el rol "Administrador"
    Entonces la operación es rechazada con el mensaje "La empresa debe tener al menos un administrador activo"

  @UC-TEN-03 @critico @RF-TEN-01 @RF-TEN-49
  Esquema del escenario: Permisos de las plantillas de rol iniciales sin modificar
    Dado el usuario "<email>" con el rol "<rol>" en "Cervecería Andina"
    Cuando intenta "<accion>"
    Entonces el resultado es "<resultado>"

    Ejemplos:
      | email           | rol        | accion                      | resultado  |
      | ana@andina.pe   | Ventas     | registrar una venta         | permitido  |
      | ana@andina.pe   | Ventas     | anular una venta            | denegado   |
      | ana@andina.pe   | Ventas     | ver el estado de resultados | denegado   |
      | mario@andina.pe | Producción | iniciar una OP              | permitido  |
      | mario@andina.pe | Producción | registrar una compra        | denegado   |
      | rosa@andina.pe  | Almacén    | registrar un ajuste         | permitido  |
      | rosa@andina.pe  | Almacén    | anular una compra           | denegado   |
      | jose@andina.pe  | Gerente    | anular una venta            | permitido  |
      | jose@andina.pe  | Gerente    | crear un usuario            | denegado   |

  @UC-TEN-03 @RN-GEN-01 @critico @RF-TEN-52
  Escenario: Aislamiento entre empresas
    Dado que "Brew Lima" tiene el producto "Stout botella 330 ml"
    Cuando "lucia@andina.pe" busca productos
    Entonces no ve el producto "Stout botella 330 ml"
    Y si intenta abrir ese producto por su identificador recibe "No encontrado"

  @UC-TEN-03 @critico @RF-TEN-53
  Esquema del escenario: No se pueden dar permisos que uno mismo no tiene
    Dado el usuario "jose@andina.pe" con el rol "Gerente" y el permiso "core.usuario.gestionar"
    Cuando "jose@andina.pe" intenta <accion>
    Entonces la operación es rechazada con el mensaje "<mensaje>"

    Ejemplos:
      | accion                                                  | mensaje                                                  |
      | asignarse el rol "Administrador"                        | Solo un administrador puede asignar el rol Administrador |
      | asignar a "ana@andina.pe" un rol con "core.rol.gestionar" | No puedes dar permisos que no tienes                   |

  @UC-TEN-03 @RF-TEN-13
  Escenario: Los usuarios no se borran, se desactivan
    Dado que "mario@andina.pe" registró la compra "C-000001"
    Cuando "lucia@andina.pe" desactiva a "mario@andina.pe"
    Entonces "mario@andina.pe" no puede iniciar sesión
    Y la compra "C-000001" sigue mostrando a "mario@andina.pe" como autor
    Y no existe la opción de eliminar usuarios
