# Tareas 0001c — Usuarios, roles y permisos

Estado: **implementada** (2026-10-10). 22/22 tareas hechas; escenarios en verde salvo los parciales anotados.

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Dominio puro

- [x] **T1. Implementar `permisos_efectivos` y `origen_permisos`.** — RF-TEN-10, RF-TEN-14, RF-TEN-37, RF-TEN-39, RF-TEN-41
  - Hecho cuando: `test_permisos.py` comprueba que:
    - los permisos de dos roles se unen;
    - el rol de sistema tiene todos los permisos habilitados;
    - un permiso de una funcionalidad quitada sigue en el rol, pero no es efectivo;
    - un rol inactivo no suma permisos;
    - un usuario sin roles tiene un conjunto vacío.
- [x] **T2. Implementar `validar_permisos_rol` y `validar_escalada`.** — RF-TEN-36, RF-TEN-53
  - Hecho cuando: un test comprueba que:
    - dar un permiso que el actor no tiene lanza `EscaladaDePrivilegios`;
    - un actor que no es Administrador no puede asignar el rol Administrador, y un Administrador sí;
    - un permiso no habilitado lanza `PermisoNoHabilitado`.
- [x] **T3. Implementar `cabe_en_limite` y `quedan_administradores`.** — RF-TEN-11, RF-TEN-12
  - Hecho cuando: un test comprueba que un límite `None` es ilimitado, que con 3 usuarios activos y límite 3 ya no cabe otro, y que quitar el único Administrador activo devuelve `False`.
- [x] **T4. Crear las plantillas de rol iniciales y `roles_iniciales(habilitadas)`.** — RF-TEN-01
  - Hecho cuando: `test_plantillas.py` reproduce la tabla de la spec, verifica que cada permiso existe en `CATALOGO` y comprueba que se recortan a las funcionalidades habilitadas.
  - Nota: supuesto, porque la tabla no lo detalla: "stock y kardex" incluye `inventario.lote.ver`; Gerente y Almacén gestionan almacenes; "Compras" incluye proveedores. Ver `tenancy/domain/plantillas.py`.

## Persistencia y autorización transversal

- [x] **T5. Crear los modelos de rol, rol-permiso y usuario-rol.** — RF-TEN-10, RF-TEN-35
  - Hecho cuando: un test comprueba `UNIQUE(empresa_id, nombre)` y que solo hay un rol de sistema por empresa.
  - Nota: `rol_permiso` y `usuario_rol` usan `id` + `UNIQUE` en vez de PK compuesta, para poder usar `ManyToManyField` (`Usuario.roles`).
- [x] **T6. Crear el sembrador de roles y registrarlo en 0001a.** — RF-TEN-01
  - Hecho cuando: después de registrar una empresa, existen el rol "Administrador" (sistema), "Gerente", "Producción", "Almacén" y "Ventas", y el primer usuario tiene el rol "Administrador" ("Roles iniciales al registrar la empresa" en verde).
- [x] **T7. Crear `Actor` y la clase base `CasoDeUso` con `permiso_requerido`, y el meta-test de autorización.** — RF-TEN-49, RNF-TEN-06
  - Hecho cuando: `tests/meta/test_autorizacion.py` comprueba que todo `CasoDeUso` declara un permiso del catálogo y que se rechaza sin ese permiso.
  - Nota: `CasoDeUso.__init_subclass__` envuelve `ejecutar(actor, …)` para exigir el permiso antes de todo; el meta-test recorre `src/*/application`.
- [x] **T8. Crear `AccesoMiddleware`, que construye el `Actor` en cada request.** — RF-TEN-40, RF-TEN-42
  - Hecho cuando: en `test_acceso_mw.py`, si se quita la funcionalidad entre dos requests, la segunda recibe "Esta funcionalidad ya no está disponible en tu plan" y no guarda nada.
  - Nota: `AccesoMiddleware.process_exception` convierte `AccesoDenegado` en 403 (con el mensaje de RF-TEN-42) y `NoEncontrado` en 404.
- [x] **T9. Crear las páginas "Acceso denegado" (403), "No encontrado" (404) y "Sin módulos asignados".** — RF-TEN-41, RF-TEN-49, RF-TEN-52
  - Hecho cuando: "Usuario sin permisos efectivos" está en verde y un test comprueba que un id de otra empresa da 404.
- [x] **T10. Crear el template tag `{% puede %}` y el menú lateral.** — RF-TEN-50
  - Hecho cuando: `test_ui_permisos.py` comprueba que un módulo sin permisos no aparece en el menú y que un botón sin permiso no se muestra.
  - Nota: en vez de un template tag, un context processor expone `permisos` (`{% if "x" in permisos %}`); el menú filtra por el `permiso` de cada opción.
- [x] **T11. Crear el meta-test de aislamiento.** — RF-TEN-52, RNF-TEN-05
  - Hecho cuando: `tests/meta/test_aislamiento.py` recorre todos los modelos con `empresa_id` y todas las rutas con `<id>`, y "Aislamiento entre empresas" está en verde.
  - Nota: el meta-test exige que toda ruta de empresa con `<int:…>` esté en su tabla `RUTAS`; así una ruta nueva sin prueba de aislamiento hace fallar la suite.

## Usuarios

- [x] **T12. Crear los casos de uso `CrearUsuario` y `EditarUsuario`, con el límite del plan.** — RF-TEN-10, RF-TEN-11, RF-TEN-13
  - Hecho cuando: `test_usuarios.py` comprueba que:
    - los usuarios técnicos no cuentan para el límite;
    - reactivar un usuario por encima del límite se rechaza;
    - no existe ninguna operación de borrado de usuarios ("Los usuarios no se borran, se desactivan" en verde).
- [x] **T13. Crear `AsignarRoles` con control de escalada.** — RF-TEN-10, RF-TEN-53
  - Hecho cuando: "No se pueden dar permisos que uno mismo no tiene" está en verde y un test comprueba que un Administrador puede asignar cualquier rol.
- [x] **T14. Crear `CambiarEstadoUsuario`, con lock para no dejar a la empresa sin administrador.** — RF-TEN-12
  - Hecho cuando: "El último administrador no puede desactivarse" está en verde y, en `test_concurrencia.py`, si dos administradores se desactivan entre sí a la vez, uno de los dos es rechazado.
- [x] **T15. Crear `PermisosEfectivosQuery` y la ficha del usuario.** — RF-TEN-14
  - Hecho cuando: "Ver los permisos efectivos de un usuario" está en verde.
- [x] **T16. Crear las pantallas `/usuarios/`: listado y formulario con varios roles.** — RF-TEN-10, RF-TEN-11
  - Hecho cuando: "Administrador crea un usuario con un rol", "Límite de usuarios del plan" y "Permisos efectivos con varios roles" están en verde.

## Roles

- [x] **T17. Crear `CrearRol`, `EditarRol` y `DuplicarRol`, con validación de habilitaciones.** — RF-TEN-35, RF-TEN-36
  - Hecho cuando: "El servidor rechaza permisos no habilitados" está en verde con un formulario manipulado.
- [x] **T18. Hacer no editable el rol Administrador y crear `DesactivarRol` y `EliminarRol`.** — RF-TEN-37, RF-TEN-38
  - Hecho cuando: "El rol Administrador no se edita", "El Administrador recibe automáticamente lo que se habilita después" y "Rol con usuarios se desactiva en vez de eliminarse" están en verde.
- [x] **T19. Crear la pantalla `/roles/` con la matriz módulo → funcionalidad → permisos.** — RF-TEN-35, RF-TEN-39
  - Hecho cuando: "Crear un rol propio con permisos habilitados", "El editor de roles bloquea lo no habilitado" y "Los permisos dejan de ser efectivos si la plataforma quita la funcionalidad" están en verde.
- [x] **T20. Crear el helper común para ocultar costos sin `inventario.costo.ver` (pantalla, CSV y API).** — RF-TEN-51
  - Hecho cuando: `test_ui_permisos.py` comprueba que el helper omite las columnas de costo en los tres formatos. "Ocultar costos a un rol" queda para cuando exista la pantalla de stock (épica 0003).
  - Nota: helper `shared/interfaces/costos.py::sin_costos`. "Ocultar costos a un rol" queda como skip parcial hasta la pantalla de stock (0003c).
- [x] **T21. Probar la autorización en el servidor para cada acción de la tabla.** — RF-TEN-49
  - Hecho cuando: "Autorización en el servidor por permiso" y "Permisos de las plantillas de rol iniciales sin modificar" están en verde para las acciones ya implementadas; el resto queda para su spec.
  - Nota: "puede <acción>" se verifica con el `Actor` (el mismo control que hará cada caso de uso). Con acción real: "crear un usuario". Skip parcial con motivo: anular una venta, registrar una compra, ver el estado de resultados, generar un token de API (0001d); aislamiento de productos (0002a); autor de compras (0004a); menú de ajustes (0003b).

## Cierre

- [x] **T22. Verificar la spec completa.** — RF-TEN-10 a RF-TEN-14, RF-TEN-35 a RF-TEN-42, RF-TEN-49 a RF-TEN-53
  - Hecho cuando:
    - `pytest tests/tenancy tests/meta tests/acceptance -k "E01c or meta"` está en verde, salvo los escenarios parciales de T20 y T21;
    - el lint, `lint-imports` y `makemigrations --check` están en verde;
    - cada RF de la spec tiene un escenario `@RF-TEN-…` o un test que lo cita;
    - `MEMORY.md` está actualizado.
