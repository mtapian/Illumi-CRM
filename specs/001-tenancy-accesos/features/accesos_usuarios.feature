# language: es
@E01 @mvp
Característica: Inicio de sesión, usuarios y plantillas de rol
  Como administrador de una empresa
  Quiero controlar quién accede y qué puede hacer
  Para proteger la información de mi negocio

  Antecedentes:
    Dado la empresa "Cervecería Andina" con plan que permite 10 usuarios
    Y la empresa "Brew Lima" con datos propios
    Y el usuario "lucia@andina.pe" con el rol "Administrador" de "Cervecería Andina"
    Y "Cervecería Andina" tiene habilitados todos los módulos

  @UC-TEN-02 @critico @RF-TEN-06
  Escenario: Inicio de sesión exitoso
    Cuando "lucia@andina.pe" inicia sesión con su contraseña correcta
    Entonces accede al dashboard de "Cervecería Andina"

  @UC-TEN-02 @borde @RF-TEN-07
  Escenario: Usuario inactivo no puede iniciar sesión
    Dado que el usuario "pedro@andina.pe" está inactivo
    Cuando "pedro@andina.pe" inicia sesión con su contraseña correcta
    Entonces el acceso es rechazado con el mensaje "Tu usuario está desactivado. Contacta al administrador."

  @UC-TEN-02 @borde @RF-TEN-08
  Escenario: Bloqueo temporal por intentos fallidos
    Cuando "lucia@andina.pe" falla la contraseña 5 veces seguidas
    Entonces su usuario queda bloqueado durante 15 minutos
    Y un intento con la contraseña correcta dentro de ese plazo es rechazado

  @UC-TEN-02 @RF-TEN-09
  Escenario: Recuperación de contraseña
    Cuando "lucia@andina.pe" solicita recuperar su contraseña
    Entonces recibe un email con un enlace de un solo uso válido por 60 minutos
    Y al usar el enlace puede definir una nueva contraseña
    Y el enlace ya no puede reutilizarse

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

  @UC-TEN-04 @RF-TEN-15
  Escenario: Configurar datos de empresa
    Cuando "lucia@andina.pe" actualiza el nombre comercial a "Andina Brewing" y el logo
    Entonces el menú lateral muestra "Andina Brewing" y el nuevo logo
    Y el RUC no es editable

  @UC-TEN-04 @borde @RF-TEN-16
  Escenario: El cambio de IGV no afecta documentos existentes
    Dado una venta emitida con IGV 18 %
    Cuando "lucia@andina.pe" cambia el IGV a 10 %
    Entonces la venta existente mantiene su IGV de 18 %
    Y las ventas nuevas usan 10 %
