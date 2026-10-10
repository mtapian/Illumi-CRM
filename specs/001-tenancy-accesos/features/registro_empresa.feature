# language: es
@E01 @mvp
Característica: Registro de empresa con prueba gratis
  Como dueño de una cervecera
  Quiero registrar mi empresa en la plataforma
  Para empezar a operar con un periodo de prueba

  Antecedentes:
    Dado que la plataforma tiene configurados 14 días de prueba
    Y que existe el plan de prueba "Negocio"

  @UC-TEN-01 @critico @RF-TEN-01 @RF-TEN-05 @RF-INV-01 @RF-CAT-01 @RF-FIN-03
  Escenario: Registro exitoso crea empresa, administrador y datos iniciales
    Cuando me registro con:
      | campo        | valor                   |
      | ruc          | 20601234565             |
      | razon_social | Cervecería Andina S.A.C. |
      | nombre       | Lucía Torres            |
      | email        | lucia@andina.pe         |
      | password     | Clave-Segura-2026       |
    Entonces se crea la empresa "Cervecería Andina S.A.C." en estado "trial"
    Y la prueba termina 14 días después de hoy
    Y "lucia@andina.pe" es administrador activo de esa empresa
    Y la empresa tiene el almacén "Principal"
    Y la empresa tiene las unidades de medida iniciales "UND, KG, G, L, ML"
    Y la empresa tiene las categorías de gasto iniciales
    Y quedo autenticado en el dashboard de la empresa

  @UC-TEN-01 @borde @RF-TEN-03
  Esquema del escenario: Registro rechazado por RUC inválido
    Cuando me registro con el RUC "<ruc>"
    Entonces el registro es rechazado con el mensaje "<mensaje>"
    Y no se crea ninguna empresa ni usuario

    Ejemplos:
      | ruc          | mensaje                                   |
      | 2060123456   | El RUC debe tener 11 dígitos              |
      | 30601234567  | El RUC debe empezar con 10, 15, 17 o 20   |
      | 20601234560  | El RUC no es válido                       |

  @UC-TEN-01 @borde @RF-TEN-03
  Escenario: Registro rechazado por RUC ya registrado
    Dado que existe una empresa con RUC "20601234565"
    Cuando me registro con el RUC "20601234565"
    Entonces el registro es rechazado con el mensaje "Ya existe una empresa con este RUC"

  @UC-TEN-01 @borde @RF-TEN-04
  Escenario: Registro rechazado por email ya usado
    Dado que existe un usuario con email "lucia@andina.pe"
    Cuando me registro con el email "lucia@andina.pe"
    Entonces el registro es rechazado con el mensaje "Este email ya está registrado"
    Y no se crea ninguna empresa

  @UC-TEN-01 @critico @borde @RF-TEN-02
  Escenario: Falla en la creación de datos iniciales revierte el registro
    Dado que la creación del almacén inicial va a fallar
    Cuando me registro con datos válidos
    Entonces no se crea ninguna empresa ni usuario
    Y veo un mensaje de error genérico para reintentar
