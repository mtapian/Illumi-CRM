# language: es
@E01 @mvp
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

  @UC-TEN-06 @critico @RF-TEN-22
  Escenario: Super admin activa un plan
    Dado que "Cervecería Andina" tiene la prueba vencida
    Cuando el super admin activa el plan "Negocio" hasta el "2026-12-31" con el motivo "Pago transferencia"
    Entonces la empresa queda en estado "activa" hasta el "2026-12-31"
    Y sus usuarios pueden operar normalmente
    Y el registro de actividad guarda la acción, el super admin, la fecha y el motivo

  @UC-TEN-06 @RF-TEN-22
  Escenario: Super admin suspende y reactiva
    Cuando el super admin suspende "Cervecería Andina" con el motivo "Falta de pago"
    Entonces la empresa queda en estado "suspendida"
    Cuando el super admin la reactiva
    Entonces la empresa vuelve al estado anterior a la suspensión
