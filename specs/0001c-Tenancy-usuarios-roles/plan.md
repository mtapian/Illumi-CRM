# Plan 0001c — Usuarios, roles y permisos

Estado: borrador

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contextos: `src/shared/application/autorizacion.py` (autorización transversal) y `src/tenancy` (usuarios y roles). Requiere 0001a y 0001b.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/shared/application/autorizacion.py` | `Actor` (permisos efectivos) y clase base `CasoDeUso` con `permiso_requerido` | RF-TEN-49 |
| `src/shared/interfaces/costos.py` | Helper común que omite costos unitarios y valorización sin `inventario.costo.ver` (pantalla, CSV y API) | RF-TEN-51 |
| `src/tenancy/domain/permisos.py` | Funciones puras de permisos efectivos y control de escalada | RF-TEN-10, 14, 36, 37, 39, 41, 53 |
| `src/tenancy/domain/plantillas.py` | Plantillas de rol iniciales como datos (tabla de la spec) | RF-TEN-01 |
| `src/tenancy/domain/errores.py` (**modifica**) | `LimiteUsuariosPlan`, `UltimoAdministrador`, `EscaladaDePrivilegios`, `PermisoNoHabilitado`, `RolConUsuarios` | todos los `SI … ENTONCES` |
| `src/tenancy/application/sembrador_roles.py` | Sembrador de 0001a: crea el rol de sistema y las plantillas filtradas por habilitaciones, y asigna "Administrador" al primer usuario | RF-TEN-01 |
| `src/tenancy/application/usuarios.py` | `CrearUsuario`, `EditarUsuario`, `AsignarRoles`, `CambiarEstadoUsuario`, `PermisosEfectivosQuery` | RF-TEN-10 a 14, 53 |
| `src/tenancy/application/roles.py` | `CrearRol`, `EditarRol`, `DuplicarRol`, `DesactivarRol`, `EliminarRol` | RF-TEN-35 a 39 |
| `src/tenancy/infrastructure/models.py` (**modifica**) | Modelos de §2 | §2 |
| `src/tenancy/interfaces/middleware.py` (**modifica**) | `AccesoMiddleware`: construye el `Actor` en cada request | RF-TEN-40, 41, 42 |
| `src/tenancy/interfaces/templatetags/acceso.py` | `{% puede "permiso" %}` para menú y botones | RF-TEN-50 |
| `src/tenancy/interfaces/views/*.py` + `templates/tenancy/*.html` | Pantallas de §5 y páginas 403/404/"sin módulos" | RF-TEN-10 a 14, 35 a 42, 52 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `tenancy_rol` | empresa_id, nombre, es_sistema, activo | UNIQUE(empresa_id, nombre); un solo rol de sistema por empresa | RF-TEN-35, 37, 38 |
| `tenancy_rol_permiso` | rol_id, permiso_codigo | PK compuesta; se conserva aunque el permiso deje de estar habilitado | RF-TEN-35, 39 |
| `tenancy_usuario_rol` | usuario_id, rol_id | PK compuesta | RF-TEN-10, 12 |

## 3. Funciones puras (dominio, sin base de datos)

| Función | Qué hace | RF |
|---|---|---|
| `permisos_efectivos(roles_activos, habilitadas) -> frozenset` | Rol de sistema ⇒ todos los habilitados; si no, `(∪ roles) ∩ permisos(habilitadas)` | RF-TEN-10, 37, 39, 41 |
| `origen_permisos(roles, habilitadas) -> dict` | Para la ficha: permiso → roles que lo dan, o "no disponible por el plan" | RF-TEN-14 |
| `validar_permisos_rol(permisos, habilitadas)` | Lanza `PermisoNoHabilitado` | RF-TEN-36 |
| `validar_escalada(permisos_actor, es_admin_actor, permisos_a_dar, da_rol_admin)` | Lanza `EscaladaDePrivilegios` | RF-TEN-53 |
| `quedan_administradores(usuarios_activos_admin_despues) -> bool` | Al menos un Administrador activo | RF-TEN-12 |
| `cabe_en_limite(activos_no_tecnicos, limite) -> bool` | `limite is None or activos < limite` | RF-TEN-11 |
| `roles_iniciales(habilitadas) -> list` | Plantillas recortadas a las funcionalidades habilitadas | RF-TEN-01 |

## 4. Algoritmos clave (pseudocódigo)

**Construcción del `Actor` en cada request** (RF-TEN-40, 41, 42, 49):
```
AccesoMiddleware(request):
  u = request.user; e = u.empresa
  habilitadas = TenancyService.habilitaciones_de(e, hoy)        # se recalcula en cada request: RF-TEN-40, 42
  permisos = permisos_efectivos(roles_activos(u), habilitadas)
  request.actor = Actor(u, e, permisos)
  si permisos vacío → pantalla "No tienes módulos asignados"   # RF-TEN-41
```

**Asignar roles sin escalada** (RF-TEN-10 a 12, 53):
```
AsignarRoles(actor, usuario, roles_nuevos):
  actor.exige(core.usuario.gestionar)
  validar_escalada(actor.permisos, actor.es_admin, ∪permisos(roles_nuevos), "Administrador" ∈ roles_nuevos)
  con lock de la empresa:                                     # dos admins en paralelo
     si not quedan_administradores(admins_activos_tras_el_cambio) → UltimoAdministrador
     guardar
```

## 5. Interfaz

El menú y los botones se pintan con `{% puede %}` (RF-TEN-50).

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/usuarios/` | Listado; formulario con selección múltiple de roles; ficha con permisos efectivos agrupados por módulo y su origen | RF-TEN-10 a 14, 53 |
| `/roles/` | Matriz módulo → funcionalidad → permisos (casillas; las no habilitadas en gris con "No incluido en tu plan"); acciones duplicar, desactivar, eliminar | RF-TEN-35 a 39 |
| Páginas "Acceso denegado" (403), "No encontrado" (404) y "Sin módulos asignados" | Mensajes de la spec; un registro de otra empresa siempre da 404 | RF-TEN-41, 42, 49, 52 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Permisos efectivos recalculados en cada request (2 consultas) | Caché con versión por empresa | Simplicidad (art. 7.6) y aplicación inmediata de cambios (RF-TEN-40); se agrega caché solo si se mide lentitud |
| Un registro de otra empresa responde 404 | Responder 403 | No revela que el registro existe (caso límite de la spec, art. 3) |
| Roles iniciales sembrados por el sembrador de 0001a | Crearlos dentro de `RegistrarEmpresa` | Mantiene 0001a independiente de esta spec |
| Helper de costos en `shared/interfaces` | Que cada pantalla filtre los costos por su cuenta | Una sola regla para pantallas, CSV y API (RF-TEN-51) |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/tenancy tests/meta tests/acceptance -k "E01c or meta"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/tenancy/unit/test_permisos.py` | Unión de roles ∩ habilitadas, rol de sistema, rol inactivo, permisos conservados no efectivos, escalada, límite, último administrador | RF-TEN-10, 11, 12, 14, 36, 37, 39, 41, 53 |
| Unitario | `tests/tenancy/unit/test_plantillas.py` | Las plantillas reproducen la tabla de la spec y usan permisos del catálogo | RF-TEN-01 |
| Caso de uso | `tests/tenancy/usecases/test_usuarios.py` | Límite sin técnicos, último administrador, no borrar, escalada | RF-TEN-10 a 13, 53 |
| Caso de uso | `tests/tenancy/usecases/test_roles.py` | Rol con permiso no habilitado, Administrador no editable, rol con usuarios | RF-TEN-35 a 38 |
| Integración | `tests/tenancy/integration/test_acceso_mw.py` | Cambios aplicados en la siguiente request; funcionalidad quitada rechaza sin guardar | RF-TEN-40, 41, 42 |
| Integración | `tests/tenancy/integration/test_concurrencia.py` | Dos admins se desactivan a la vez (`TransactionTestCase`) | RF-TEN-12 |
| Integración | `tests/tenancy/integration/test_ui_permisos.py` | Menú y botones según permisos; costos ocultos en pantalla, CSV y API | RF-TEN-50, 51 |
| Meta-test | `tests/meta/test_autorizacion.py` | Todo `CasoDeUso` declara un permiso del catálogo y falla sin él (cubre las épicas 0001–0008) | RF-TEN-49, RNF-TEN-06 |
| Meta-test | `tests/meta/test_aislamiento.py` | Todos los modelos de empresa y rutas con `<id>`: datos de B invisibles desde A (404) | RF-TEN-52, RNF-TEN-05 |
| Aceptación | `features/*.feature` (2 archivos) | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-TEN-10, RF-TEN-11, RF-TEN-12, RF-TEN-13, RF-TEN-14, RF-TEN-53 | §1 `usuarios.py`, `permisos.py` · §3 `cabe_en_limite`, `quedan_administradores`, `origen_permisos`, `validar_escalada` · §4 asignar roles · §5 `/usuarios/` · §7 |
| RF-TEN-35, RF-TEN-36, RF-TEN-37, RF-TEN-38, RF-TEN-39 | §1 `roles.py`, `permisos.py` · §2 `tenancy_rol*` · §3 `validar_permisos_rol`, `permisos_efectivos` · §5 `/roles/` · §7 |
| RF-TEN-40, RF-TEN-41, RF-TEN-42 | §1 `middleware.py` · §4 construcción del Actor · §5 403/"sin módulos" · §7 `test_acceso_mw.py` |
| RF-TEN-49, RF-TEN-50, RF-TEN-51, RF-TEN-52 | §1 `autorizacion.py`, `acceso.py`, `costos.py` · §5 menú y 404 · §7 meta-tests y `test_ui_permisos.py` |
| RF-TEN-01 (roles iniciales) | §1 `sembrador_roles.py`, `plantillas.py` · §3 `roles_iniciales` · §7 `test_plantillas.py` |

## 9. Dependencias de dudas abiertas

- **Wireframe de "Roles y permisos":** cambia solo la plantilla de `/roles/`.
- **épica 0003:** la verificación completa de RF-TEN-51 en la pantalla de stock llega con esa spec; aquí se prueba el helper.
