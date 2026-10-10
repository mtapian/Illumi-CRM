# language: es
@E01 @E01d @mvp
Característica: Tokens de API para integraciones
  Como administrador de una empresa
  Quiero crear tokens de API con permisos limitados
  Para integrar el sistema con n8n sin compartir contraseñas

  Antecedentes:
    Dado la empresa "Cervecería Andina" con la funcionalidad "API de integración" habilitada
    Y la empresa "Brew Lima" con datos propios
    Y "lucia@andina.pe" tiene el rol "Administrador"

  @UC-TEN-11 @critico @RF-TEN-45 @RF-TEN-43
  Escenario: El token se muestra completo una sola vez
    Cuando "lucia@andina.pe" crea el token "n8n-stock" para el usuario técnico "n8n" con el rol "Almacén"
    Entonces ve el token completo una sola vez con el botón "Copiar"
    Y al recargar la página solo ve su prefijo, la fecha de creación y el último uso
    Y la auditoría registra la creación del token "n8n-stock"

  @UC-TEN-11 @RF-TEN-48 @RF-TEN-52
  Escenario: Una llamada con token solo ve datos de su empresa
    Dado el token "n8n-stock" de "Cervecería Andina"
    Cuando una integración consulta el stock con ese token
    Entonces recibe solo productos de "Cervecería Andina", paginados
    Y no recibe datos de "Brew Lima"

  @UC-TEN-11 @borde @RF-TEN-47 @RF-TEN-43
  Escenario: Un token revocado deja de funcionar de inmediato
    Dado el token "n8n-stock" de "Cervecería Andina"
    Cuando "lucia@andina.pe" revoca "n8n-stock"
    Entonces la siguiente llamada con ese token es rechazada como no autenticada
    Y la auditoría registra la revocación

  @UC-TEN-11 @borde @RF-TEN-54
  Escenario: Desactivar el usuario técnico invalida todos sus tokens
    Dado que el usuario técnico "n8n" tiene los tokens "n8n-stock" y "n8n-ventas"
    Cuando "lucia@andina.pe" desactiva el usuario técnico "n8n"
    Entonces las llamadas con "n8n-stock" y con "n8n-ventas" son rechazadas como no autenticadas

  @UC-TEN-11 @borde @RF-TEN-46
  Esquema del escenario: Tokens rechazados por el estado de la empresa
    Dado el token "n8n-stock" de "Cervecería Andina"
    Y que <situacion>
    Cuando una integración consulta el stock con ese token
    Entonces la llamada es rechazada

    Ejemplos:
      | situacion                                                        |
      | "Cervecería Andina" está suspendida                              |
      | la suscripción de "Cervecería Andina" venció ayer                |
      | la funcionalidad "API de integración" fue quitada a la empresa   |

  @UC-TEN-11 @borde @RF-TEN-46
  Escenario: Sin API de integración no se crean tokens
    Dado que la funcionalidad "API de integración" no está habilitada para "Cervecería Andina"
    Cuando "lucia@andina.pe" intenta crear un token
    Entonces la operación es rechazada con el mensaje "Tu plan no incluye la API de integración"
