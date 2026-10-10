# Tareas 0001a — Registro, sesión y suscripción

Estado: borrador (ejemplo). **No ejecutar:** `spec.md` y `plan.md` siguen en borrador (constitución, art. 2.1) y dependen de Q6.

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Base del proyecto (plan 000)

- [ ] **T1. Crear el proyecto Django 5.2 con `config/` y `src/`, y las dependencias fijadas en `pyproject.toml`.** — (plan 000)
  - Hecho cuando: `python manage.py check` no da errores y `pytest` se ejecuta con 0 tests.
- [ ] **T2. Configurar ruff e import-linter con los contratos de capas y contextos.** — (plan 000)
  - Hecho cuando: `ruff check` y `lint-imports` están en verde, y un import de `domain` hacia `infrastructure` agregado a propósito hace fallar `lint-imports`.
- [ ] **T3. Configurar pytest-django con PostgreSQL 16 y pytest-bdd sobre `specs/*/features`.** — (plan 000)
  - Hecho cuando: `pytest --collect-only tests/acceptance -k E01a` lista los escenarios de los 3 `.feature` de esta spec.
- [ ] **T4. Crear `TenantContext` y un manager base que falla si no hay tenant.** — (plan 000 §4)
  - Hecho cuando: un test comprueba que una consulta sin tenant lanza un error y que, con el tenant A, no aparecen filas de B.
- [ ] **T5. Crear `shared_secuencia` y `SequencePort.siguiente()` con `select_for_update`.** — (numeración de todas las specs)
  - Hecho cuando: un test con 2 hilos obtiene los números 1 y 2, sin duplicados ni huecos.

## Dominio puro

- [ ] **T6. Crear el value object `Ruc`.** — RF-TEN-03
  - Hecho cuando: `test_ruc.py` está en verde con estos casos: `20601234565` es válido; se rechazan un RUC de 10 dígitos, uno con prefijo `30` y uno con dígito verificador errado.
- [ ] **T7. Implementar `valor_vigente()` y `validar_igv()`.** — RF-TEN-16
  - Hecho cuando: `test_vigencia.py` comprueba el valor el día antes, el mismo día y el día después de un cambio, y que `100.001` se rechaza.
- [ ] **T8. Implementar `estado_suscripcion`, `dias_para_vencer`, `mostrar_aviso_vencimiento` y `fecha_termino_prueba`, todas con `hoy`.** — RF-TEN-05, RF-TEN-18, RF-TEN-19, RF-TEN-20
  - Hecho cuando: `test_suscripcion.py` comprueba que:
    - si `hoy == fecha_termino`, no está vencida, y con `hoy + 1` está `VENCIDA`;
    - el aviso aparece con 7 días y no con 8;
    - `SUSPENDIDA` prevalece sobre la fecha.
- [ ] **T9. Implementar `bloqueo_por_intentos`.** — RF-TEN-08
  - Hecho cuando: `test_sesion.py` comprueba que el 5.º fallo bloquea durante 15 minutos y el 4.º no bloquea.

## Persistencia

- [ ] **T10. Crear los modelos de plan (básico), empresa y parámetro con vigencia.** — RF-TEN-05, RF-TEN-16, RF-TEN-17
  - Hecho cuando: un test comprueba `UNIQUE(ruc)`, que no puede haber dos planes de prueba activos y que `tenancy_parametro_vigencia` rechaza `UPDATE`.
- [ ] **T11. Crear el modelo de usuario (`AUTH_USER_MODEL`).** — RF-TEN-04, RF-TEN-06
  - Hecho cuando: un test comprueba `UNIQUE(email)` y que un usuario técnico no puede autenticarse.
- [ ] **T12. Crear los repositorios y la fachada `TenancyService` (`igv_vigente`, `parametro_vigente`, `empresa_activa`).** — RF-TEN-16, RF-TEN-18
  - Hecho cuando: un test comprueba que `igv_vigente(fecha)` respeta la vigencia y que `empresa_activa` usa `estado_suscripcion`.

## Registro

- [ ] **T13. Crear el puerto `SembradorInicial` y `registrar_sembrador()`.** — RF-TEN-01
  - Hecho cuando: un test registra dos sembradores falsos y comprueba que se ejecutan en orden con la empresa, el administrador y `hoy`.
- [ ] **T14. Crear el caso de uso `RegistrarEmpresa` en una sola transacción.** — RF-TEN-01, RF-TEN-02, RF-TEN-03, RF-TEN-04, RF-TEN-05
  - Hecho cuando: `test_registro.py` comprueba que:
    - la empresa queda `TRIAL` con fecha de término hoy + 14;
    - se rechazan un RUC duplicado y un email duplicado;
    - si un sembrador falso falla, no queda ninguna empresa ni ningún usuario;
    - un doble envío crea una sola empresa.
- [ ] **T15. Crear la vista `/registro` con su plantilla.** — RF-TEN-01 a RF-TEN-05
  - Hecho cuando: los escenarios de `registro_empresa.feature` están en verde. "Registro exitoso" queda parcial hasta que 0001c, 002, 003, 006, 007 y 008 registren sus sembradores.

## Sesión

- [ ] **T16. Crear el login con un mensaje para cada motivo de rechazo.** — RF-TEN-06, RF-TEN-07
  - Hecho cuando:
    - "Inicio de sesión exitoso" y "Usuario inactivo no puede iniciar sesión" están en verde;
    - el super admin llega a `/plataforma`;
    - un usuario de una empresa suspendida recibe el mensaje del motivo.
- [ ] **T17. Bloquear al usuario tras varios intentos fallidos.** — RF-TEN-08
  - Hecho cuando: el escenario "Bloqueo temporal por intentos fallidos" está en verde.
- [ ] **T18. Crear el outbox de correos `shared_correo`, `encolar_correo()` y el comando de envío.** — RF-TEN-09
  - Hecho cuando: un test comprueba que un correo encolado en una transacción revertida no existe, y que el comando lo envía con el backend `locmem` y lo marca enviado.
- [ ] **T19. Crear la recuperación de contraseña.** — RF-TEN-09
  - Hecho cuando: el escenario "Recuperación de contraseña" está en verde, y el enlace se rechaza si se usa por segunda vez o después de 61 minutos.
- [ ] **T20. Configurar la seguridad en `config/settings.py`: HTTPS, expiración de la sesión y hasher de contraseñas.** — RNF-TEN-01, RNF-TEN-03, RNF-TEN-04
  - Hecho cuando: `python manage.py check --deploy` no da advertencias.

## Empresa y suscripción

- [ ] **T21. Crear los casos de uso `ActualizarEmpresa` y `CambiarIgv`, con vigencia.** — RF-TEN-15, RF-TEN-16, RF-TEN-17
  - Hecho cuando: `test_empresa.py` comprueba que el RUC no se puede editar y que, con el IGV cambiado desde mañana, `igv_vigente(hoy)` sigue en 18.
- [ ] **T22. Crear la pantalla `/configuracion/empresa`.** — RF-TEN-15, RF-TEN-16, RF-TEN-17
  - Hecho cuando: "Configurar datos de empresa" y "El cambio de IGV no afecta documentos existentes" están en verde.
- [ ] **T23. Crear `TenantMiddleware` y `SuscripcionMiddleware`.** — RF-TEN-18, RF-TEN-21
  - Hecho cuando: "Prueba vencida bloquea la operación" y "Suspensión con sesión abierta" están en verde, y logout sigue disponible.
- [ ] **T24. Crear el comando `vencer_suscripciones` y la página `/suscripcion`.** — RF-TEN-18, RF-TEN-20
  - Hecho cuando: el comando marca `VENCIDA` sin borrar filas (el conteo de cada tabla es igual antes y después).
- [ ] **T25. Mostrar en el dashboard el aviso de vencimiento y la guía de primeros pasos.** — RF-TEN-05, RF-TEN-19
  - Hecho cuando: "Banner de días de prueba restantes" está en verde.

## Cierre

- [ ] **T26. Verificar la spec completa.** — RF-TEN-01 a RF-TEN-09, RF-TEN-15 a RF-TEN-21
  - Hecho cuando:
    - `pytest tests/shared tests/tenancy tests/acceptance -k E01a` está en verde, salvo la parte de "Registro exitoso" que depende de otras specs;
    - el lint, `lint-imports` y `makemigrations --check` están en verde;
    - cada RF de la spec tiene un escenario `@RF-TEN-…` o un test que lo cita;
    - `MEMORY.md` está actualizado.
