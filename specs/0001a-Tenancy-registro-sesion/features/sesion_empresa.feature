# language: es
@E01 @E01a @mvp
Característica: Inicio de sesión y datos de la empresa
  Como usuario de una empresa
  Quiero entrar con mi email y mantener los datos fiscales al día
  Para trabajar con la información de mi negocio

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
