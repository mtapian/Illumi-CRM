# Spec 0001d — Auditoría de accesos y tokens de API

Estado: implementada (2026-10-10)

Épica E01 (Tenancy y accesos), parte 4 de 4. Depende de: 0001a, 0001b, 0001c.

## Contexto y objetivo

Una empresa necesita saber quién cambió los accesos de sus usuarios (constitución, art. 6.4) e integrar el sistema con herramientas como n8n sin compartir contraseñas.

**Objetivo:** que todo cambio de acceso quede auditado y que las integraciones lean solo los datos de su empresa con permisos limitados.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Administrador de la empresa | Consulta la auditoría y crea o revoca tokens de API |
| Super admin (plataforma) | Consulta además el historial de habilitaciones de una empresa |
| Integración (n8n u otra) | Lee datos de la empresa con un token |

## Historias de usuario

- H1: Como administrador, quiero ver quién cambió roles, permisos y usuarios para auditar los accesos.
- H2: Como administrador, quiero crear tokens de API con permisos limitados para integrar el sistema con n8n u otras herramientas.

## Definiciones

- **Usuario técnico:** usuario que no puede iniciar sesión en la interfaz y es dueño de uno o más tokens de API; sus roles (spec 0001c) definen qué puede leer cada token. Se crea y gestiona solo desde UC-TEN-11 y no cuenta para el límite de usuarios del plan.

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-TEN-10 Consultar la auditoría de accesos

- RF-TEN-43: CUANDO cambia un rol, sus permisos, la asignación de roles de un usuario o el estado de un usuario, o cuando se crea o revoca un token de API, EL SISTEMA registra quién, cuándo y el valor anterior y el nuevo (RN-TEN-14).
- RF-TEN-44: CUANDO un usuario con `core.auditoria.ver` consulta la auditoría, EL SISTEMA muestra ese historial con filtros; el super admin ve además el historial de habilitaciones de la empresa.

### UC-TEN-11 Gestionar tokens de API

- RF-TEN-45: CUANDO un usuario con `api.token.gestionar` crea un token con nombre, asociado a un usuario técnico (que crea si no existe), EL SISTEMA muestra el token completo **una única vez, en ese momento**, para que se copie; nunca lo guarda en claro y después solo muestra su prefijo, la fecha de creación y el último uso.
- RF-TEN-46: SI la funcionalidad "API de integración" no está habilitada para la empresa, o la empresa está suspendida o con la suscripción vencida, ENTONCES EL SISTEMA rechaza crear tokens y rechaza las llamadas con tokens existentes.
- RF-TEN-47: CUANDO se revoca un token, EL SISTEMA lo invalida de inmediato.
- RF-TEN-54: CUANDO se desactiva un usuario técnico, EL SISTEMA invalida de inmediato todos sus tokens.
- RF-TEN-48: CUANDO llega una llamada con un token válido, EL SISTEMA responde solo con datos de la empresa del token y según los permisos del usuario técnico. Las consultas disponibles en el MVP son stock, pedidos, ventas, productos y estado de resultados, todos paginados (cada una se implementa en su spec).

## Requisitos no funcionales

- RNF-TEN-02: Los tokens de API se guardan de forma que no se puedan recuperar en claro.

## Casos límite

- Se pierde un token: no se puede volver a mostrar; se revoca y se crea otro.
- La empresa se suspende con integraciones activas: sus llamadas se rechazan desde ese momento (RF-TEN-46).

## Fuera de alcance

Escritura por API (el MVP solo expone consultas, RF-TEN-48).

## Criterios de finalización

- Escenarios de `features/` en verde.
- Cada RF-TEN de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- Ninguna.
