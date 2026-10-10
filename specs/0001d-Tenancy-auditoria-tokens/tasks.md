# Tareas 0001d — Auditoría de accesos y tokens de API

Estado: borrador (ejemplo). **No ejecutar:** `spec.md` y `plan.md` siguen en borrador (constitución, art. 2.1). Requiere 0001a, 0001b y 0001c terminadas.

Spec: `./spec.md` · Plan: `./plan.md`

Reglas (constitución, art. 8):
- Una tarea a la vez, de 30 minutos como máximo.
- Primero el test en rojo; después el código, hasta que el test pase a verde; marcar la tarea y parar.
- Además de su "Hecho cuando", cada tarea exige `ruff check`, `ruff format --check`, `lint-imports` y `python manage.py makemigrations --check` en verde.

## Auditoría

- [ ] **T1. Crear el modelo de auditoría, el trigger `auditoria_inmutable.sql` y `registrar_auditoria()`.** — RF-TEN-43
  - Hecho cuando: un test de integración comprueba que un `UPDATE` o un `DELETE` sobre `tenancy_auditoria_acceso` falla en la base de datos.
- [ ] **T2. Auditar los cambios de roles y permisos.** — RF-TEN-43
  - Hecho cuando: un test comprueba que crear, editar, duplicar y desactivar un rol deja una auditoría `ROL` con el valor anterior y el nuevo.
- [ ] **T3. Auditar las asignaciones de roles y los cambios de estado de usuarios.** — RF-TEN-43
  - Hecho cuando: un test comprueba que `AsignarRoles` deja una auditoría `USUARIO_ROL` y que `CambiarEstadoUsuario` deja una auditoría `USUARIO`, ambas con el valor anterior y el nuevo.
- [ ] **T4. Crear `AuditoriaAccesosQuery` y la pantalla `/auditoria/accesos`.** — RF-TEN-44
  - Hecho cuando: "Auditoría de cambios de acceso" está en verde, con filtros por fecha, entidad y autor, y el super admin ve además el historial de habilitaciones de la empresa.

## Tokens de API

- [ ] **T5. Implementar `prefijo_token` y `token_utilizable`.** — RF-TEN-46, RF-TEN-47, RF-TEN-54
  - Hecho cuando: una tabla de casos devuelve `False` con un token revocado, un usuario técnico inactivo, una empresa suspendida o vencida, o la API no habilitada, y `True` con todo en orden.
- [ ] **T6. Crear el modelo `tenancy_api_token`.** — RF-TEN-45
  - Hecho cuando: un test comprueba `UNIQUE(token_hash)` y que el modelo no tiene ningún campo con el token en claro.
- [ ] **T7. Crear `CrearTokenApi`: usuario técnico, hash SHA-256, token visible una sola vez y auditoría.** — RF-TEN-43, RF-TEN-45, RF-TEN-46
  - Hecho cuando: un test comprueba que:
    - el token en claro solo aparece en la respuesta de creación;
    - la base de datos guarda solo el hash;
    - queda una auditoría `TOKEN_API`;
    - sin la API habilitada, la creación se rechaza ("Sin API de integración no se crean tokens" en verde).
- [ ] **T8. Crear `RevocarTokenApi` e invalidar los tokens al desactivar el usuario técnico.** — RF-TEN-43, RF-TEN-47, RF-TEN-54
  - Hecho cuando: "Un token revocado deja de funcionar de inmediato" y "Desactivar el usuario técnico invalida todos sus tokens" están en verde.
- [ ] **T9. Crear `TokenActorAuthentication` para DRF y un endpoint de prueba paginado.** — RF-TEN-46, RF-TEN-48
  - Hecho cuando: `test_api_token.py` comprueba que:
    - con la empresa suspendida o vencida se responde 401;
    - con la API no habilitada se responde 403;
    - solo se devuelven datos de la empresa del token;
    - "Una llamada con token solo ve datos de su empresa" y "Tokens rechazados por el estado de la empresa" están en verde.

    Los endpoints de stock, pedidos, ventas, productos y estado de resultados quedan para sus specs.
- [ ] **T10. Crear la pantalla `/integracion/tokens`.** — RF-TEN-45, RF-TEN-47
  - Hecho cuando: "El token se muestra completo una sola vez" está en verde y el token completo no aparece en el listado ni al recargar la página.

## Cierre

- [ ] **T11. Verificar la spec completa.** — RF-TEN-43 a RF-TEN-48, RF-TEN-54
  - Hecho cuando:
    - `pytest tests/tenancy tests/acceptance -k E01d` está en verde;
    - el lint, `lint-imports` y `makemigrations --check` están en verde;
    - cada RF de la spec tiene un escenario `@RF-TEN-…` o un test que lo cita;
    - `MEMORY.md` está actualizado.
