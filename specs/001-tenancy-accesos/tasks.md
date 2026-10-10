# Tareas 001 — Tenancy y accesos

Estado: borrador (ejemplo). **No ejecutar:** `spec.md` y `plan.md` siguen en borrador (constitución, art. 2.1) y dependen de Q6 y Q8.

Spec: `./spec.md` · Plan: `./plan.md` · Base técnica: `../000-arquitectura/plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Una tarea está hecha cuando, además de lo que indica su "Hecho cuando", `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` están en verde.

## Fase 0 — Base del proyecto (plan 000)

- [ ] **T1. Crear el proyecto Django 5.2 con `config/` y `src/`, y las dependencias fijadas en `pyproject.toml`.** — (plan 000, ADR-01)
  - Hecho cuando: `python manage.py check` no da errores y `pytest` se ejecuta con 0 tests.
- [ ] **T2. Configurar ruff e import-linter con los contratos de capas y contextos.** — (plan 000, capas)
  - Hecho cuando: `ruff check`, `ruff format --check` y `lint-imports` están en verde, y un import de `domain` hacia `infrastructure` agregado a propósito hace fallar `lint-imports`.
- [ ] **T3. Configurar pytest-django con PostgreSQL 16 y pytest-bdd sobre `specs/*/features`.** — (plan 000, ADR-09)
  - Hecho cuando: `pytest --collect-only tests/acceptance -k E01` lista los escenarios de los 5 `.feature` de la spec 001.
- [ ] **T4. Crear `TenantContext` y un manager base que falla si no hay tenant.** — RF-TEN-52
  - Hecho cuando: un test comprueba que una consulta sin tenant lanza un error y que, con el tenant A, no aparecen filas de B.
- [ ] **T5. Crear `shared_secuencia` y `SequencePort.siguiente()` con `select_for_update`.** — (numeración de todas las specs)
  - Hecho cuando: un test con 2 hilos obtiene los números 1 y 2, sin duplicados ni huecos.

## Fase 1 — Dominio puro (sin base de datos)

- [ ] **T6. Crear el value object `Ruc`.** — RF-TEN-03
  - Hecho cuando: `tests/tenancy/unit/test_ruc.py` está en verde con estos casos: `20601234565` es válido; se rechazan un RUC de 10 dígitos, uno con prefijo `30` y uno con dígito verificador errado.
- [ ] **T7. Implementar `valor_vigente()` y `validar_igv()`.** — RF-TEN-16
  - Hecho cuando: `tests/shared/unit/test_vigencia.py` comprueba el valor el día antes, el mismo día y el día después de un cambio, y que `100.001` se rechaza.
- [ ] **T8. Implementar `estado_suscripcion`, `dias_para_vencer`, `mostrar_aviso_vencimiento` y `fecha_termino_prueba`, todas con `hoy`.** — RF-TEN-05, RF-TEN-18, RF-TEN-19, RF-TEN-20
  - Hecho cuando: `test_suscripcion.py` comprueba que:
    - si `hoy == fecha_termino`, no está vencida, y con `hoy + 1` está `VENCIDA`;
    - el aviso aparece con 7 días y no con 8;
    - `SUSPENDIDA` prevalece sobre la fecha.
- [ ] **T9. Crear el catálogo `shared/domain/accesos.py` (`CATALOGO`, `P`, dependencias) y `dependencias_faltantes()`.** — RF-TEN-26, RF-TEN-31, RF-TEN-35
  - Hecho cuando: un test comprueba que el catálogo no tiene ciclos y que todo permiso pertenece a una funcionalidad. Además, "Envasado multipresentación" sin sus dependencias devuelve `[Recetas, Órdenes de producción]`.
- [ ] **T10. Implementar `ajuste_vigente`, `habilitaciones_efectivas` y `estado_funcionalidad`.** — RF-TEN-28, RF-TEN-30, RF-TEN-33
  - Hecho cuando: `test_habilitaciones.py` comprueba que:
    - un ajuste que vence hoy sigue vigente y uno que venció ayer no;
    - CORE siempre está presente;
    - se obtienen los 4 estados: Incluida, Agregada, Quitada y No incluida.
- [ ] **T11. Implementar `dependientes_afectados` y `funcionalidades_de_modulo`.** — RF-TEN-31, RF-TEN-34
  - Hecho cuando: un test comprueba que quitar "Stock y kardex" devuelve Ajustes de inventario, Compras y proveedores, y Ventas, y que CORE no se puede quitar.
- [ ] **T12. Implementar `permisos_efectivos` y `origen_permisos`.** — RF-TEN-10, RF-TEN-14, RF-TEN-37, RF-TEN-39, RF-TEN-41
  - Hecho cuando: `test_permisos.py` comprueba que:
    - los permisos de dos roles se unen;
    - el rol de sistema tiene todos los permisos habilitados;
    - un permiso de una funcionalidad quitada sigue en el rol, pero no es efectivo;
    - un rol inactivo no suma permisos;
    - un usuario sin roles tiene un conjunto vacío.
- [ ] **T13. Implementar `validar_permisos_rol` y `validar_escalada`.** — RF-TEN-36, RF-TEN-53
  - Hecho cuando: un test comprueba que:
    - dar un permiso que el actor no tiene lanza `EscaladaDePrivilegios`;
    - un actor que no es Administrador no puede asignar el rol Administrador, y un Administrador sí;
    - un permiso no habilitado lanza `PermisoNoHabilitado`.
- [ ] **T14. Implementar `cabe_en_limite`, `quedan_administradores` y `bloqueo_por_intentos`.** — RF-TEN-08, RF-TEN-11, RF-TEN-12
  - Hecho cuando: un test comprueba que:
    - un límite `None` es ilimitado;
    - con 3 usuarios activos y límite 3 ya no cabe otro;
    - el 5.º fallo bloquea durante 15 minutos y el 4.º no bloquea.
- [ ] **T15. Implementar `prefijo_token` y `token_utilizable`.** — RF-TEN-46, RF-TEN-47, RF-TEN-54
  - Hecho cuando: una tabla de casos devuelve `False` con un token revocado, un usuario técnico inactivo, una empresa suspendida o vencida, o la API no habilitada, y `True` con todo en orden.
- [ ] **T16. Crear las plantillas de rol iniciales como datos (`plantillas.py`).** — RF-TEN-01
  - Hecho cuando: un test reproduce la tabla de plantillas de la spec y verifica que cada permiso existe en `CATALOGO`.

## Fase 2 — Persistencia

- [ ] **T17. Crear los modelos de plan, módulo, funcionalidad, permiso, dependencia y plan-funcionalidad, con su migración.** — RF-TEN-25, RF-TEN-26
  - Hecho cuando: la migración se aplica y un test de integración comprueba `UNIQUE(slug)` y que no puede haber dos planes de prueba activos.
- [ ] **T18. Crear la data migration `0002_catalogo`, que sincroniza `CATALOGO` con sus tablas.** — RF-TEN-35
  - Hecho cuando: un test comprueba que:
    - después de migrar, las tablas coinciden con `CATALOGO`;
    - ejecutarla dos veces no cambia nada;
    - un código retirado queda `obsoleto` y no se borra.
- [ ] **T19. Crear los modelos de empresa, ajuste de empresa, parámetro con vigencia y actividad.** — RF-TEN-15, RF-TEN-17, RF-TEN-18, RF-TEN-22, RF-TEN-29
  - Hecho cuando: un test comprueba `UNIQUE(ruc)`, que hay un solo ajuste activo por funcionalidad y que `tenancy_parametro_vigencia` rechaza `UPDATE`.
- [ ] **T20. Crear el modelo de usuario (`AUTH_USER_MODEL`) y los de rol, rol-permiso y usuario-rol.** — RF-TEN-06, RF-TEN-10, RF-TEN-13
  - Hecho cuando: un test comprueba `UNIQUE(email)` y `UNIQUE(empresa_id, nombre)` en los roles, y que el repositorio de usuarios no tiene ninguna operación de borrado.
- [ ] **T21. Crear el modelo de auditoría, el trigger `auditoria_inmutable.sql` y `registrar_auditoria()`.** — RF-TEN-43
  - Hecho cuando: un test de integración comprueba que un `UPDATE` o un `DELETE` sobre `tenancy_auditoria_acceso` falla en la base de datos.
- [ ] **T22. Crear los repositorios de tenancy y la fachada `TenancyService` (`igv_vigente`, `parametro_vigente`, `empresa_activa`).** — RF-TEN-16, RF-TEN-52
  - Hecho cuando: un test comprueba que `igv_vigente(fecha)` respeta la vigencia y que el repositorio, con el tenant A, no ve datos de B.
- [ ] **T23. Crear el modelo `tenancy_api_token`.** — RF-TEN-45
  - Hecho cuando: un test comprueba `UNIQUE(token_hash)` y que el modelo no tiene ningún campo con el token en claro.

## Fase 3 — Autorización transversal

- [ ] **T24. Crear `Actor` y la clase base `CasoDeUso` con `permiso_requerido`, y el meta-test de autorización.** — RF-TEN-49, RNF-TEN-06
  - Hecho cuando: `tests/meta/test_autorizacion.py` comprueba que todo `CasoDeUso` declara un permiso del catálogo y que se rechaza sin ese permiso.
- [ ] **T25. Crear `TenantMiddleware` y `AccesoMiddleware`, que construye el `Actor` en cada request.** — RF-TEN-40, RF-TEN-42
  - Hecho cuando: en `test_middleware.py`, si se quita la funcionalidad entre dos requests, la segunda recibe "Esta funcionalidad ya no está disponible en tu plan" y no guarda nada.
- [ ] **T26. Crear `SuscripcionMiddleware`.** — RF-TEN-18, RF-TEN-21
  - Hecho cuando: un test comprueba que:
    - una empresa vencida redirige a `/suscripcion` en todas las rutas salvo logout;
    - suspender la empresa con la sesión abierta bloquea la siguiente request.
- [ ] **T27. Crear las páginas "Acceso denegado" (403), "No encontrado" (404) y "Sin módulos asignados".** — RF-TEN-41, RF-TEN-49, RF-TEN-52
  - Hecho cuando: un test comprueba que un usuario sin permisos ve "No tienes módulos asignados…" y que un id de otra empresa da 404.
- [ ] **T28. Crear el template tag `{% puede %}` y el menú lateral.** — RF-TEN-50
  - Hecho cuando: `test_ui_permisos.py` comprueba que un módulo sin permisos no aparece en el menú y que un botón sin permiso no se muestra.
- [ ] **T29. Crear el meta-test de aislamiento.** — RF-TEN-52, RNF-TEN-05
  - Hecho cuando: `tests/meta/test_aislamiento.py` recorre todos los modelos con `empresa_id` y todas las rutas con `<id>`, y está en verde.

## Fase 4 — Registro y sesión

- [ ] **T30. Crear el caso de uso `RegistrarEmpresa` (empresa, plan de prueba, roles iniciales y administrador).** — RF-TEN-01, RF-TEN-03, RF-TEN-04, RF-TEN-05
  - Hecho cuando: `test_registro.py` comprueba que la empresa queda `TRIAL` con fecha de término hoy + 14, y que se rechazan un RUC duplicado y un email duplicado.
- [ ] **T31. Crear el puerto de sembradores iniciales y hacer atómico el registro.** — RF-TEN-01, RF-TEN-02
  - Hecho cuando: un test con un sembrador falso que falla comprueba que no queda ninguna empresa ni ningún usuario, y que un doble envío crea una sola empresa.
- [ ] **T32. Crear la vista `/registro` con su plantilla.** — RF-TEN-01 a RF-TEN-05
  - Hecho cuando: los escenarios de `registro_empresa.feature` están en verde. "Registro exitoso" queda parcial hasta que las specs 002, 003, 006, 007 y 008 registren sus sembradores.
- [ ] **T33. Crear el login con un mensaje para cada motivo de rechazo.** — RF-TEN-06, RF-TEN-07
  - Hecho cuando:
    - "Inicio de sesión exitoso" y "Usuario inactivo no puede iniciar sesión" están en verde;
    - el super admin llega a `/plataforma`;
    - un usuario técnico no puede iniciar sesión.
- [ ] **T34. Bloquear al usuario tras varios intentos fallidos.** — RF-TEN-08
  - Hecho cuando: el escenario "Bloqueo temporal por intentos fallidos" está en verde.
- [ ] **T35. Crear el outbox de correos `shared_correo`, `encolar_correo()` y el comando de envío.** — RF-TEN-09
  - Hecho cuando: un test comprueba que un correo encolado en una transacción revertida no existe, y que el comando lo envía con el backend `locmem` y lo marca enviado.
- [ ] **T36. Crear la recuperación de contraseña.** — RF-TEN-09
  - Hecho cuando: el escenario "Recuperación de contraseña" está en verde, y el enlace se rechaza si se usa por segunda vez o después de 61 minutos.
- [ ] **T37. Configurar la seguridad en `config/settings.py`: HTTPS, expiración de la sesión y hasher de contraseñas.** — RNF-TEN-01, RNF-TEN-03, RNF-TEN-04
  - Hecho cuando: `python manage.py check --deploy` no da advertencias.

## Fase 5 — Empresa y suscripción

- [ ] **T38. Crear los casos de uso `ActualizarEmpresa` y `CambiarIgv`, con vigencia.** — RF-TEN-15, RF-TEN-16, RF-TEN-17
  - Hecho cuando: `test_empresa.py` comprueba que el RUC no se puede editar y que, con el IGV cambiado desde mañana, `igv_vigente(hoy)` sigue en 18.
- [ ] **T39. Crear la pantalla `/configuracion/empresa`.** — RF-TEN-15, RF-TEN-16, RF-TEN-17
  - Hecho cuando: "Configurar datos de empresa" y "El cambio de IGV no afecta documentos existentes" están en verde.
- [ ] **T40. Crear el comando `vencer_suscripciones` y la página `/suscripcion`.** — RF-TEN-18, RF-TEN-20
  - Hecho cuando: "Prueba vencida bloquea la operación" está en verde y el comando marca `VENCIDA` sin borrar filas (el conteo de cada tabla es igual antes y después).
- [ ] **T41. Mostrar en el dashboard el aviso de vencimiento y la guía de primeros pasos.** — RF-TEN-05, RF-TEN-19
  - Hecho cuando: "Banner de días de prueba restantes" está en verde.

## Fase 6 — Usuarios

- [ ] **T42. Crear los casos de uso `CrearUsuario` y `EditarUsuario`, con el límite del plan.** — RF-TEN-10, RF-TEN-11, RF-TEN-13
  - Hecho cuando: `test_usuarios.py` comprueba que:
    - los usuarios técnicos no cuentan para el límite;
    - un límite vacío es ilimitado;
    - reactivar un usuario por encima del límite se rechaza.
- [ ] **T43. Crear `AsignarRoles` con control de escalada y auditoría.** — RF-TEN-10, RF-TEN-43, RF-TEN-53
  - Hecho cuando: un test comprueba que se rechazan los dos casos de escalada y que queda una auditoría `USUARIO_ROL` con el valor anterior y el nuevo.
- [ ] **T44. Crear `CambiarEstadoUsuario`, con lock para no dejar a la empresa sin administrador.** — RF-TEN-12, RF-TEN-43
  - Hecho cuando: en `test_concurrencia.py`, si dos administradores se desactivan entre sí a la vez, uno recibe "La empresa debe tener al menos un administrador activo".
- [ ] **T45. Crear `PermisosEfectivosQuery` y la ficha del usuario.** — RF-TEN-14
  - Hecho cuando: "Ver los permisos efectivos de un usuario" está en verde.
- [ ] **T46. Crear las pantallas `/usuarios/`: listado y formulario con varios roles.** — RF-TEN-10 a RF-TEN-14, RF-TEN-53
  - Hecho cuando: los escenarios `@UC-TEN-03` de `accesos_usuarios.feature` y `roles_permisos.feature` están en verde.

## Fase 7 — Roles y permisos

- [ ] **T47. Crear `CrearRol`, `EditarRol` y `DuplicarRol`, con validación de habilitaciones y auditoría.** — RF-TEN-35, RF-TEN-36, RF-TEN-43
  - Hecho cuando: "El servidor rechaza permisos no habilitados" está en verde con un formulario manipulado.
- [ ] **T48. Hacer no editable el rol Administrador y crear `DesactivarRol` y `EliminarRol`.** — RF-TEN-37, RF-TEN-38
  - Hecho cuando: "El rol Administrador no se edita", "El Administrador recibe automáticamente lo que se habilita después" y "Rol con usuarios se desactiva en vez de eliminarse" están en verde.
- [ ] **T49. Crear la pantalla `/roles/` con la matriz módulo → funcionalidad → permisos.** — RF-TEN-35, RF-TEN-39
  - Hecho cuando: "Crear un rol propio con permisos habilitados", "El editor de roles bloquea lo no habilitado" y "Los permisos dejan de ser efectivos si la plataforma quita la funcionalidad" están en verde.
- [ ] **T50. Crear un helper común para ocultar costos sin `inventario.costo.ver` (pantalla, CSV y API).** — RF-TEN-51
  - Hecho cuando: `test_ui_permisos.py` comprueba que el helper omite las columnas de costo en los tres formatos. "Ocultar costos a un rol" queda para cuando exista la pantalla de stock (spec 003).
- [ ] **T51. Probar la autorización en el servidor para cada acción de la tabla.** — RF-TEN-49
  - Hecho cuando: el esquema "Autorización en el servidor por permiso" está en verde para las acciones ya implementadas; el resto queda para su spec.

## Fase 8 — Auditoría

- [ ] **T52. Crear `AuditoriaAccesosQuery` y la pantalla `/auditoria/accesos`.** — RF-TEN-44
  - Hecho cuando: "Auditoría de cambios de acceso" está en verde, con filtros por fecha, entidad y autor.

## Fase 9 — Plataforma (super admin)

- [ ] **T53. Crear `ActivarPlan`, `SuspenderEmpresa` y `ReactivarEmpresa`, con motivo y actividad.** — RF-TEN-22
  - Hecho cuando: "Super admin activa un plan" y "Super admin suspende y reactiva" están en verde.
- [ ] **T54. Crear el listado `/plataforma/empresas/` con filtros por estado y plan.** — RF-TEN-24
  - Hecho cuando: un test comprueba que el super admin filtra sin elegir una empresa y que un usuario de empresa recibe 403.
- [ ] **T55. Crear `ConfigurarFuncionalidadesPlan`, con dependencias y límites.** — RF-TEN-25, RF-TEN-26
  - Hecho cuando: "Agregar una funcionalidad a un plan valida sus dependencias" está en verde.
- [ ] **T56. Mostrar la vista previa de impacto y aplicar el cambio a todas las empresas del plan.** — RF-TEN-27
  - Hecho cuando: "Cambio en el plan impacta a todas sus empresas" está en verde y los ajustes propios de cada empresa no cambian.
- [ ] **T57. Crear `CambiarPlan`, que conserva los ajustes de la empresa.** — RF-TEN-23
  - Hecho cuando: "Al cambiar de plan se conservan los ajustes de la empresa" está en verde.
- [ ] **T58. Crear `AgregarFuncionalidad`, `QuitarFuncionalidad` y el atajo por módulo, con motivo, vigencia, dependencias y auditoría.** — RF-TEN-29, RF-TEN-31, RF-TEN-33, RF-TEN-34
  - Hecho cuando: están en verde estos escenarios:
    - "Agregar un módulo a una empresa con vigencia";
    - "Quitar una funcionalidad incluida en el plan solo para una empresa";
    - "No se quita una dependencia de otra funcionalidad habilitada";
    - "Ajuste sin motivo es rechazado";
    - "CORE no se puede deshabilitar".
- [ ] **T59. Crear `ImpactoQuitarQuery`, con un puerto en el que cada spec aporta su contador de operaciones en curso.** — RF-TEN-32
  - Hecho cuando: "Advertencia al quitar un módulo con operaciones en curso" está en verde con un contador falso de OP; el contador real llega con la spec 005.
- [ ] **T60. Crear la pantalla `/plataforma/empresas/<id>/modulos`, con estados y vencimiento de ajustes.** — RF-TEN-28, RF-TEN-30
  - Hecho cuando: "Vista de estado de habilitaciones de la empresa" y "Vence la vigencia de un ajuste" están en verde, este último con `hoy` fijado al día siguiente al fin del ajuste.

## Fase 10 — Tokens de API

- [ ] **T61. Crear `CrearTokenApi`: usuario técnico, hash SHA-256, token visible una sola vez y auditoría.** — RF-TEN-43, RF-TEN-45
  - Hecho cuando: un test comprueba que el token en claro solo aparece en la respuesta de creación, que la base de datos guarda solo el hash y que queda una auditoría `TOKEN_API`.
- [ ] **T62. Crear `RevocarTokenApi` e invalidar los tokens al desactivar el usuario técnico.** — RF-TEN-47, RF-TEN-54
  - Hecho cuando: un test comprueba que, en ambos casos, la siguiente llamada con ese token recibe 401.
- [ ] **T63. Crear `TokenActorAuthentication` para DRF y un endpoint de prueba paginado.** — RF-TEN-46, RF-TEN-48
  - Hecho cuando: `test_api_token.py` comprueba que:
    - con la empresa suspendida o vencida se responde 401;
    - con la API no habilitada se responde 403;
    - solo se devuelven datos de la empresa del token.

    Los endpoints de stock, pedidos, ventas y producción quedan para sus specs.
- [ ] **T64. Crear la pantalla `/integracion/tokens`.** — RF-TEN-45, RF-TEN-47
  - Hecho cuando: un test de la vista comprueba que el token completo no aparece en el listado ni al recargar la página.

## Fase 11 — Cierre de la spec

- [ ] **T65. Verificar la spec completa.** — todos los RF-TEN
  - Hecho cuando:
    - `pytest tests/tenancy tests/meta tests/acceptance -k E01` está en verde, salvo los escenarios `@pendiente-q*` y los parciales de T32 y T50;
    - el lint, `lint-imports` y `makemigrations --check` están en verde;
    - cada RF-TEN tiene un escenario `@RF-TEN-…` o un test que lo cita;
    - `MEMORY.md` está actualizado.
