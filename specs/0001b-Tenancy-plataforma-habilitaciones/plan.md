# Plan 0001b — Plataforma: planes y habilitaciones

Estado: borrador

Spec: `./spec.md` · Base técnica: `../0000-Arquitectura/plan.md` · Constitución: `../../docs/constitution.md` (v1.1.0)

Contextos: `src/shared/domain/accesos.py` (catálogo de permisos como código, usado por todos los contextos) y `src/tenancy` (planes, ajustes y habilitaciones). Requiere 0001a.

## 1. Archivos y responsabilidades

| Archivo | Responsabilidad | RF |
|---|---|---|
| `src/shared/domain/accesos.py` | Catálogo de módulos, funcionalidades, permisos y dependencias como constantes (`CATALOGO`, clase `P` con los códigos) | RF-TEN-25, 26, 31, 34 |
| `src/tenancy/domain/habilitaciones.py` | Funciones puras de habilitaciones, dependencias y vigencia de ajustes | RF-TEN-26, 28, 30, 31, 33, 34 |
| `src/tenancy/domain/errores.py` (**modifica**) | `DependenciasFaltantes`, `DependientesHabilitados`, `MotivoObligatorio`, `CoreNoSeQuita` | todos los `SI … ENTONCES` |
| `src/tenancy/application/operaciones_en_curso.py` | Puerto `ContadorOperacionesEnCurso` y registro `registrar_contador()`; cada contexto registra los suyos | RF-TEN-32 |
| `src/tenancy/application/plataforma.py` | `ActivarPlan`, `SuspenderEmpresa`, `ReactivarEmpresa`, `CambiarPlan`, `ConfigurarFuncionalidadesPlan`, `AgregarFuncionalidad`, `QuitarFuncionalidad`, `RevocarAjuste`, `ImpactoQuitarQuery`, `EmpresasQuery` | RF-TEN-22 a 34 |
| `src/tenancy/application/fachada.py` (**modifica**) | `habilitaciones_de(empresa, hoy)`, `registrar_contador()` | RF-TEN-30, 32 |
| `src/tenancy/infrastructure/models.py` (**modifica**) | Modelos de §2 | §2 |
| `src/tenancy/infrastructure/migrations/0002_catalogo.py` | Data migration que sincroniza `CATALOGO` con sus tablas | RF-TEN-25 |
| `src/tenancy/interfaces/views/plataforma/*.py` + `templates/tenancy/plataforma/*.html` | Pantallas de §5; solo para `is_super` | RF-TEN-22 a 34 |

## 2. Modelo de datos

| Tabla | Campos | Restricciones | RF |
|---|---|---|---|
| `tenancy_modulo`, `tenancy_funcionalidad`, `tenancy_permiso`, `tenancy_funcionalidad_dependencia` | códigos, nombres, módulo, dependencias, `obsoleto` | Sincronizados desde `CATALOGO`; nunca se borran códigos con referencias | RF-TEN-26, 31 |
| `tenancy_plan_funcionalidad` | plan_id, funcionalidad_codigo | PK compuesta | RF-TEN-25, 27 |
| `tenancy_empresa_ajuste` | empresa_id, funcionalidad_codigo, tipo (`AGREGAR`/`QUITAR`), vigente_hasta `DATE` null, motivo, creado_por, creado_en, revocado_en | Un ajuste activo por funcionalidad | RF-TEN-29, 30 |
| `tenancy_actividad` | empresa_id, actor_id, accion, motivo, created_at | Solo inserción | RF-TEN-22 |

Son datos de plataforma: el super admin los administra sin elegir una empresa (constitución, art. 3.1).

## 3. Funciones puras (dominio, sin base de datos)

| Función | Qué hace | RF |
|---|---|---|
| `ajuste_vigente(ajuste, hoy) -> bool` | `vigente_hasta is None or hoy <= vigente_hasta` | RF-TEN-30 |
| `habilitaciones_efectivas(funcs_plan, ajustes, hoy) -> frozenset` | `CORE ∪ (plan ∪ agregados vigentes) − quitados vigentes` | RF-TEN-23, 28, 30, 33 |
| `estado_funcionalidad(f, funcs_plan, ajustes, hoy) -> str` | Incluida / Agregada / Quitada / No incluida | RF-TEN-28 |
| `dependencias_faltantes(conjunto) -> list` | Funcionalidades requeridas que no están en el conjunto | RF-TEN-26, 31 |
| `dependientes_afectados(f, conjunto) -> list` | Funcionalidades habilitadas que dejarían de cumplir sus dependencias si se quita `f` | RF-TEN-31 |
| `funcionalidades_de_modulo(modulo) -> list` | Para habilitar o deshabilitar un módulo completo | RF-TEN-34 |

## 4. Algoritmos clave (pseudocódigo)

**Quitar una funcionalidad a una empresa** (RF-TEN-29, 31, 32, 33):
```
QuitarFuncionalidad(empresa, f, motivo, vigente_hasta, confirmado):
  exigir motivo                                                     # RF-TEN-29
  si f ∈ CORE → CoreNoSeQuita
  afectados = dependientes_afectados(f, habilitaciones_efectivas(…, hoy))
  si afectados → DependientesHabilitados(afectados)                 # RF-TEN-31
  si no confirmado:
     devolver Σ c.contar(empresa) para cada contador registrado de f  # RF-TEN-32
  guardar ajuste QUITAR (motivo, vigente_hasta, creado_por)
  # no se borra ningún dato ni rol (RF-TEN-33)
```

**Cambio en un plan** (RF-TEN-25 a 27):
```
ConfigurarFuncionalidadesPlan(plan, funcs, limites, confirmado):
  si dependencias_faltantes(funcs) → DependenciasFaltantes        # RF-TEN-26
  si no confirmado: devolver contar empresas con ese plan          # RF-TEN-27
  reemplazar tenancy_plan_funcionalidad; los ajustes de cada empresa no se tocan
```

Las habilitaciones no se copian a cada empresa: se calculan con `habilitaciones_efectivas` en cada request, así que el cambio aplica de inmediato y el vencimiento de un ajuste no necesita cron (RF-TEN-27, 30).

## 5. Interfaz

| Ruta | Qué se pinta | RF |
|---|---|---|
| `/plataforma/empresas/` | Listado con filtros por estado y plan; activar, suspender, reactivar con motivo | RF-TEN-22 a 24 |
| `/plataforma/planes/<id>` | Checklist de funcionalidades por módulo, límites; al guardar, modal "Afecta a N empresas" | RF-TEN-25 a 27 |
| `/plataforma/empresas/<id>/modulos` | Estado por funcionalidad (insignias); agregar o quitar con motivo y fecha de fin; modal de impacto; atajo por módulo | RF-TEN-28 a 34 |

## 6. Decisiones técnicas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Catálogo de permisos como código en `shared` | Permisos de Django por modelo (`add_`, `change_`) | Los permisos son por caso de uso y por funcionalidad comercial, no CRUD por tabla (constitución art. 6.1) |
| Habilitaciones calculadas (plan ± ajustes vigentes), no copiadas | Tabla de habilitaciones por empresa actualizada al cambiar plan o ajustes | Un solo lugar de verdad; el vencimiento de ajustes y los cambios de plan aplican sin procesos (RF-TEN-27, 30) |
| Operaciones en curso por **contadores registrados**: cada contexto registra los suyos en `TenancyService` | `ImpactoQuitarQuery` consulta directamente las tablas de producción y facturación | Tenancy no depende de los demás contextos; 005 y 007 agregan sus contadores cuando existen |

## 7. Estrategia de tests (pytest)

Comando: `pytest tests/tenancy tests/acceptance -k "E01b"`.

| Nivel | Archivo | Qué prueba | RF |
|---|---|---|---|
| Unitario | `tests/shared/unit/test_catalogo.py` | Catálogo sin ciclos; todo permiso pertenece a una funcionalidad | RF-TEN-26, 31 |
| Unitario | `tests/tenancy/unit/test_habilitaciones.py` | Plan ± ajustes, vigencia el día exacto, dependencias, módulo completo, 4 estados | RF-TEN-26, 28, 30, 31, 33, 34 |
| Caso de uso | `tests/tenancy/usecases/test_plataforma.py` | Activar, suspender, reactivar, cambiar plan con ajustes, impacto con contador falso | RF-TEN-22 a 27, 29, 32 |
| Integración | `tests/tenancy/integration/test_catalogo_migracion.py` | La data migration es idempotente y marca obsoletos sin borrar | RF-TEN-25 |
| Integración | `tests/tenancy/integration/test_plataforma_vistas.py` | Solo el super admin accede; listado con filtros | RF-TEN-24 |
| Aceptación | `features/*.feature` (2 archivos) | Escenarios de la spec | ver etiquetas `@RF-…` |

## 8. Cobertura de RF

| RF | Partes del plan |
|---|---|
| RF-TEN-22, RF-TEN-23, RF-TEN-24 | §1 `plataforma.py` · §2 `tenancy_actividad` · §3 `habilitaciones_efectivas` · §5 `/plataforma/empresas/` · §7 `test_plataforma.py` |
| RF-TEN-25, RF-TEN-26, RF-TEN-27 | §1 `accesos.py`, `plataforma.py`, `0002_catalogo` · §3 `dependencias_faltantes` · §4 cambio en un plan · §5 `/plataforma/planes/<id>` · §7 |
| RF-TEN-28, RF-TEN-29, RF-TEN-30, RF-TEN-31, RF-TEN-32, RF-TEN-33, RF-TEN-34 | §1 `plataforma.py`, `habilitaciones.py`, `operaciones_en_curso.py` · §3 `ajuste_vigente`, `habilitaciones_efectivas`, `estado_funcionalidad`, `dependientes_afectados`, `funcionalidades_de_modulo` · §4 quitar funcionalidad · §5 `/plataforma/empresas/<id>/modulos` · §6 contadores · §7 |

## 9. Dependencias de dudas abiertas

- **Q8:** contenido de cada plan; es dato (`tenancy_plan`, `tenancy_plan_funcionalidad`), no cambia el código.
- **épica 0005 y 007:** registran los contadores de OP en proceso y comprobantes pendientes; hasta entonces, RF-TEN-32 se verifica con un contador falso.
