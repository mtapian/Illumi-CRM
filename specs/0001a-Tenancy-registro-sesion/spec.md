# Spec 0001a — Registro, sesión y suscripción

Estado: implementada (2026-10-10; "Registro exitoso" y "El cambio de IGV…" quedan parciales hasta 0001c, 0002a, 0003a, 0006b y 0008a)

Épica E01 (Tenancy y accesos), parte 1 de 4. Depende de: ninguna. La usan: 0001b, 0001c, 0001d y 002–008.

## Contexto y objetivo

Cada cervecera (empresa) necesita un espacio propio, con sus datos aislados de los de las demás, al que entra con su email y contraseña. Este espacio lo crea ella misma con una prueba gratis. La plataforma necesita restringir el acceso de las empresas que no pagan sin borrar sus datos.

**Objetivo:** que una empresa se registre y empiece a operar en minutos, y que solo entren a operar las empresas con la prueba o la suscripción vigente.

## Usuarios / actores

| Usuario | Qué hace en esta spec |
|---|---|
| Visitante | Registra su empresa con prueba gratis |
| Usuario de la empresa | Inicia sesión y recupera su contraseña |
| Administrador de la empresa | Configura los datos fiscales de la empresa |
| Plataforma | Restringe el acceso de las empresas vencidas o suspendidas |

## Historias de usuario

- H1: Como visitante, quiero registrar mi empresa con una prueba gratis para empezar a usar el sistema sin hablar con ventas.
- H2: Como usuario, quiero iniciar sesión con mi email y contraseña para trabajar con los datos de mi empresa.
- H3: Como administrador, quiero configurar los datos fiscales de mi empresa para que aparezcan en los comprobantes.
- H4: Como plataforma, quiero restringir el acceso de una empresa con la suscripción vencida o suspendida para cobrar el servicio sin borrar sus datos.

## Definiciones

- **Empresa (tenant):** cliente del SaaS. Sus datos nunca son visibles para otra empresa.
- **Vencimiento de la prueba o la suscripción:** la empresa opera hasta el final del día de la fecha de término (hora de Lima) y queda vencida desde el día siguiente. Renovar es activar un plan con una nueva fecha de término (spec 0001b, RF-TEN-22).
- **Datos iniciales de la empresa:** lo que cada spec necesita que exista desde el registro: el almacén "Principal" (003), las unidades de medida (002), las categorías de gasto (008), las series de facturación (007), el cliente genérico (006), las habilitaciones del plan de prueba (0001b) y los roles iniciales (0001c, "Plantillas de rol iniciales").

## Requisitos funcionales (criterios de aceptación en EARS)

### UC-TEN-01 Registrar empresa con prueba gratis

- RF-TEN-01: CUANDO un visitante envía el registro con RUC, razón social, nombre comercial (opcional), su nombre, email y contraseña, EL SISTEMA crea en una sola operación la empresa, su usuario administrador, el almacén "Principal", las unidades de medida SUNAT básicas, las categorías de gasto, las series de facturación por defecto, las habilitaciones del plan de prueba y los roles iniciales.
- RF-TEN-02: SI cualquier paso del registro falla, ENTONCES EL SISTEMA no crea nada (RN-TEN-01).
- RF-TEN-03: SI el RUC no tiene 11 dígitos, no empieza con 10, 15, 17 o 20, no pasa el dígito verificador (módulo 11) o ya pertenece a otra empresa, ENTONCES EL SISTEMA rechaza el registro e indica el motivo (RN-TEN-03).
- RF-TEN-04: SI el email ya existe en la plataforma, ENTONCES EL SISTEMA rechaza el registro (RN-TEN-02).
- RF-TEN-05: CUANDO el registro termina, EL SISTEMA deja la empresa en estado `trial` con el plan de prueba durante N días (14 por defecto, configurable por la plataforma), autentica al usuario y le muestra el dashboard con una guía de primeros pasos.

### UC-TEN-02 Iniciar sesión

- RF-TEN-06: CUANDO un usuario ingresa email y contraseña válidos, EL SISTEMA lo lleva al dashboard de su empresa; al super admin, al panel de plataforma.
- RF-TEN-07: SI el usuario está inactivo o su empresa está suspendida, ENTONCES EL SISTEMA no le permite entrar y muestra un mensaje que explica el motivo.
- RF-TEN-08: SI un usuario falla 5 intentos consecutivos, ENTONCES EL SISTEMA lo bloquea durante 15 minutos (valores propuestos, PRD Q6).
- RF-TEN-09: CUANDO un usuario pide recuperar su contraseña, EL SISTEMA le envía por email un enlace de un solo uso que vence en 60 minutos.

### UC-TEN-04 Configurar datos de empresa

- RF-TEN-15: CUANDO un usuario con `core.empresa.gestionar` edita la razón social, nombre comercial, dirección fiscal, ubigeo, teléfono, email o logo, EL SISTEMA guarda los cambios. (Ajustado por 0002e: el % de IGV ya no se edita aquí.)
- RF-TEN-16 (ajustado por 0002e, RF-CAT-54): EL SISTEMA registra cada cambio de IGV como una tasa nueva, con su fecha de vigencia, de los impuestos "IGV 18%" de venta y de compra (maestro de impuestos); una tasa negativa se rechaza y los documentos usan la tasa vigente a su fecha de emisión (RN-TEN-07). La configuración de la empresa solo enlaza al maestro.
- RF-TEN-17: EL SISTEMA no permite editar el RUC después del registro.

### UC-TEN-05 Restringir acceso por suscripción

- RF-TEN-18: MIENTRAS la prueba o la suscripción de una empresa estén vencidas, o la empresa esté suspendida, EL SISTEMA solo permite a sus usuarios ver la página de suscripción y cerrar sesión, y rechaza sus tokens de API (RN-TEN-06; tokens en spec 0001d, RF-TEN-46). Los envíos pendientes a SUNAT continúan (épica 0007, RF-FAC-15).
- RF-TEN-19: MIENTRAS falten 7 días o menos para que venza la prueba o la suscripción, EL SISTEMA muestra un aviso con los días restantes.
- RF-TEN-20: EL SISTEMA nunca borra datos por vencimiento o suspensión.
- RF-TEN-21: CUANDO una empresa es suspendida mientras un usuario tiene la sesión abierta, EL SISTEMA lo bloquea en su siguiente acción.

## Requisitos no funcionales

- RNF-TEN-01: Las contraseñas se guardan con un hash no reversible; nunca se muestran ni se envían en claro.
- RNF-TEN-03: La sesión expira por inactividad (tiempo según PRD Q6).
- RNF-TEN-04: Toda la plataforma se sirve solo por HTTPS.

## Casos límite

- Un doble clic en el registro no crea dos empresas.
- La prueba vence a medianoche (hora de Lima) mientras un usuario trabaja: su siguiente acción lo lleva a la página de suscripción.
- Un dato inicial de otra spec falla al crearse: el registro completo se revierte (RF-TEN-02).

## Fuera de alcance

2FA, SSO, cobro online de suscripciones, edición del RUC por soporte, impersonación de soporte.

## Criterios de finalización

- Escenarios de `features/` en verde. "Registro exitoso" queda completo cuando 002, 003, 006, 007 y 008 aportan sus datos iniciales.
- Cada RF-TEN de esta spec tiene al menos un escenario o una prueba que lo cubre.

## Dudas abiertas

- **PRD Q6 (resuelta por el PO con los valores por defecto, 2026-10-10):** 5 intentos fallidos ⇒ 15 minutos de bloqueo; la sesión expira tras 8 horas de inactividad; contraseñas con los validadores estándar (mínimo 8 caracteres, no comunes, no solo números).
