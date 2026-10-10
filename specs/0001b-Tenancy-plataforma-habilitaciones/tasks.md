# Tareas 0001b — Plataforma: planes y habilitaciones

Estado: **implementada** (2026-10-10). 16/16 tareas hechas; 13 escenarios en verde.

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Dominio puro

- [x] **T1. Crear el catálogo `shared/domain/accesos.py` (`CATALOGO`, `P`, dependencias) y `dependencias_faltantes()`.** — RF-TEN-26, RF-TEN-31
  - Hecho cuando: un test comprueba que el catálogo no tiene ciclos y que todo permiso pertenece a una funcionalidad. Además, "Envasado multipresentación" sin sus dependencias devuelve `[Recetas, Órdenes de producción]`.
  - Nota: los códigos de permiso se usan como texto validado contra `PERMISOS`; la clase `P` con constantes se omitió (no la usa nadie todavía).
- [x] **T2. Implementar `ajuste_vigente`, `habilitaciones_efectivas` y `estado_funcionalidad`.** — RF-TEN-28, RF-TEN-30, RF-TEN-33
  - Hecho cuando: `test_habilitaciones.py` comprueba que:
    - un ajuste que vence hoy sigue vigente y uno que venció ayer no;
    - CORE siempre está presente;
    - se obtienen los 4 estados: Incluida, Agregada, Quitada y No incluida.
- [x] **T3. Implementar `dependientes_afectados` y `funcionalidades_de_modulo`.** — RF-TEN-31, RF-TEN-34
  - Hecho cuando: un test comprueba que quitar "Stock y kardex" devuelve Ajustes de inventario, Compras y proveedores, y Ventas, y que CORE no se puede quitar.

## Persistencia

- [x] **T4. Crear los modelos de módulo, funcionalidad, permiso, dependencia y plan-funcionalidad, con su migración.** — RF-TEN-25, RF-TEN-26
  - Hecho cuando: la migración se aplica y un test comprueba la PK compuesta de `tenancy_plan_funcionalidad`.
- [x] **T5. Crear la data migration `0002_catalogo`, que sincroniza `CATALOGO` con sus tablas.** — RF-TEN-25
  - Hecho cuando: un test comprueba que:
    - después de migrar, las tablas coinciden con `CATALOGO`;
    - ejecutarla dos veces no cambia nada;
    - un código retirado queda `obsoleto` y no se borra.
  - Nota: en vez de una data migration fija, `sincronizar_catalogo()` corre en cada `migrate` (señal `post_migrate`): así un permiso nuevo de otra spec no necesita migración y los tests que vacían la base lo recargan. Las tablas se crean en la migración `0005_accesos_plataforma` (la `0002` ya existía).
- [x] **T6. Crear los modelos de ajuste de empresa y actividad.** — RF-TEN-22, RF-TEN-29
  - Hecho cuando: un test comprueba que hay un solo ajuste activo por funcionalidad y que `tenancy_actividad` es de solo inserción.
  - Nota: trigger de solo inserción en la migración `0006_actividad_inmutable`.
- [x] **T7. Agregar `habilitaciones_de(empresa, hoy)` a la fachada `TenancyService`.** — RF-TEN-23, RF-TEN-30
  - Hecho cuando: un test de integración comprueba que el resultado es plan ± ajustes vigentes leídos de la base de datos.

## Casos de uso y pantallas

- [x] **T8. Crear `ActivarPlan`, `SuspenderEmpresa` y `ReactivarEmpresa`, con motivo y actividad.** — RF-TEN-22
  - Hecho cuando: "Super admin activa un plan" y "Super admin suspende y reactiva" están en verde.
  - Nota: los casos de uso de la plataforma son métodos de una sola clase `Plataforma` (`activar_plan`, `suspender`, `reactivar`, `cambiar_plan`, `configurar_plan`, `agregar`, `quitar`). Toda acción exige motivo. Reactivar vuelve al estado guardado en `estado_previo`.
- [x] **T9. Crear el listado `/plataforma/empresas/` con filtros por estado y plan.** — RF-TEN-24
  - Hecho cuando: un test comprueba que el super admin filtra sin elegir una empresa y que un usuario de empresa recibe 403.
- [x] **T10. Crear `ConfigurarFuncionalidadesPlan`, con dependencias y límites.** — RF-TEN-25, RF-TEN-26
  - Hecho cuando: "Agregar una funcionalidad a un plan valida sus dependencias" está en verde.
- [x] **T11. Mostrar la vista previa de impacto y aplicar el cambio a todas las empresas del plan.** — RF-TEN-27
  - Hecho cuando: "Cambio en el plan impacta a todas sus empresas" está en verde y los ajustes propios de cada empresa no cambian.
- [x] **T12. Crear `CambiarPlan`, que conserva los ajustes de la empresa.** — RF-TEN-23
  - Hecho cuando: "Al cambiar de plan se conservan los ajustes de la empresa" está en verde.
- [x] **T13. Crear `AgregarFuncionalidad`, `QuitarFuncionalidad` y el atajo por módulo, con motivo, vigencia y dependencias.** — RF-TEN-29, RF-TEN-31, RF-TEN-33, RF-TEN-34
  - Hecho cuando: están en verde estos escenarios:
    - "Agregar un módulo a una empresa con vigencia";
    - "Quitar una funcionalidad incluida en el plan solo para una empresa";
    - "No se quita una dependencia de otra funcionalidad habilitada";
    - "Ajuste sin motivo es rechazado";
    - "CORE no se puede deshabilitar".
- [x] **T14. Crear el puerto `ContadorOperacionesEnCurso` y `ImpactoQuitarQuery`.** — RF-TEN-32
  - Hecho cuando: "Advertencia al quitar un módulo con operaciones en curso" está en verde con un contador falso de OP; el contador real llega con la épica 0005.
  - Nota: el registro de contadores es `tenancy.application.operaciones_en_curso.contadores`; el de OP lo agrega la épica 0005.
- [x] **T15. Crear la pantalla `/plataforma/empresas/<id>/modulos`, con estados y vencimiento de ajustes.** — RF-TEN-28, RF-TEN-30
  - Hecho cuando: "Vista de estado de habilitaciones de la empresa" y "Vence la vigencia de un ajuste" están en verde, este último con `hoy` fijado al día siguiente al fin del ajuste.
  - Nota: "sus datos de producción se conservan" verifica que el ajuste vencido no se borra; los datos de producción existen recién con la épica 0005. Q8: el plan de prueba incluye todas las funcionalidades (se resuelve al calcular, no se copia).

## Cierre

- [x] **T16. Verificar la spec completa.** — RF-TEN-22 a RF-TEN-34
  - Hecho cuando:
    - `pytest tests/tenancy tests/acceptance -k E01b` está en verde;
    - el lint, `lint-imports` y `makemigrations --check` están en verde;
    - cada RF de la spec tiene un escenario `@RF-TEN-…` o un test que lo cita;
    - `MEMORY.md` está actualizado.
