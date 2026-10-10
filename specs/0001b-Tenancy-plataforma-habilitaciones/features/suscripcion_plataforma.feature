# language: es
@E01 @E01b @mvp
Característica: Activación, suspensión y reactivación de empresas
  Como super admin de la plataforma
  Quiero administrar el plan y el estado de cada empresa
  Para cobrar el servicio sin borrar datos

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
