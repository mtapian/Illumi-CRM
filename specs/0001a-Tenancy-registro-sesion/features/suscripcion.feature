# language: es
@E01 @E01a @mvp
Característica: Control de acceso por suscripción
  Como operador de la plataforma
  Quiero que solo accedan las empresas con prueba o suscripción vigente
  Para sostener el modelo SaaS

  @UC-TEN-05 @RF-TEN-19
  Escenario: Banner de días de prueba restantes
    Dado que la prueba de "Cervecería Andina" vence en 5 días
    Cuando un usuario de la empresa navega por el sistema
    Entonces ve un banner "Te quedan 5 días de prueba"

  @UC-TEN-05 @critico @RF-TEN-18
  Escenario: Prueba vencida bloquea la operación
    Dado que la prueba de "Cervecería Andina" venció ayer
    Cuando un usuario de la empresa intenta abrir el módulo de ventas
    Entonces es redirigido a la página de suscripción
    Y solo puede ver la suscripción o cerrar sesión
    Y los datos de la empresa se conservan

  @UC-TEN-05 @borde @RF-TEN-21
  Escenario: Suspensión con sesión abierta
    Dado que "ana@andina.pe" tiene una sesión abierta
    Cuando el super admin suspende "Cervecería Andina"
    Y "ana@andina.pe" hace su siguiente acción
    Entonces es redirigida a la página de suscripción
