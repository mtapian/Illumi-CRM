# Constitución de Illumi-CRM

| Campo | Valor |
|---|---|
| Versión | 1.2.0 |
| Ratificada | 2026-10-10 |
| Última enmienda | 2026-10-13 (v1.2.0) |
| Dueño | Product Owner (tapiafiis@gmail.com) |

La constitución es la primera fase del flujo SDD y está por encima de todas las specs, planes y tareas. Si una spec o un plan la contradicen, gana la constitución, hasta que se enmiende según el artículo 9.

---

## Artículo 1 — Propósito

Illumi-CRM es un **ERP lite**: un CRM/ERP SaaS multiempresa para PYMEs productoras en Perú, con lo esencial de un ERP y nada más (artículo 10). El cliente piloto es una cervecera artesanal que produce a pedido y revende mercadería. Su razón de ser: que la empresa **compre, produzca, venda, facture y conozca su utilidad real en un solo sistema, sin planillas paralelas**. Visión y alcance: [PRD.md](../PRD.md).

## Artículo 2 — La spec manda

1. No se escribe código sin una `spec.md` **aprobada** y su `plan.md` **aprobado**.
2. Lo que no está en la spec no se implementa. Si falta una decisión, se para y se pregunta; la duda se registra como `[NECESITA ACLARACIÓN]`.
3. Un cambio de requisitos se hace en este orden: spec → plan → tareas → código, en el mismo cambio.
4. Ninguna fase avanza sin la aprobación explícita del PO. Las fases son: Constitución → Spec → Clarificación → Plan → Tareas → Implementación → Validación → Cambio.
5. La spec describe el **qué** y el **por qué** (historias, requisitos en EARS, casos límite). El **cómo** (stack, datos, archivos) va solo en el plan.
6. Los escenarios Gherkin de cada spec son su criterio de aceptación ejecutable.

## Artículo 3 — Los datos de cada empresa son sagrados

1. Los datos de una empresa nunca son visibles ni modificables por otra. El super admin solo ve los datos de negocio de una empresa (productos, stock, ventas, comprobantes…) si la elige explícitamente. Los datos de plataforma (empresas, planes, habilitaciones y su auditoría) los administra sin elegir una.
2. Una prueba automática de aislamiento sobre todos los datos y todas las pantallas bloquea cualquier publicación si falla.
3. Deshabilitar un módulo, vencer una suscripción o suspender una empresa nunca borra datos.

## Artículo 4 — El dinero y el inventario no se aproximan

1. Importes con 2 decimales, cantidades con 4 y costos unitarios con 6, todos con redondeo *half-up*. Nunca con aritmética de coma flotante.
2. El costo de inventario es el promedio ponderado por producto (valor total / cantidad total), sin IGV.
3. El costo de una salida se congela en el momento del movimiento y nunca se recalcula.
4. Todo cambio de stock genera exactamente un movimiento inmutable. El stock nunca es negativo.
5. Los documentos confirmados no se editan ni se borran. Se anulan cuando sus efectos pueden revertirse sin falsear el inventario, y la anulación los revierte una sola vez. Si no pueden revertirse (p. ej. una compra ya consumida, una OP terminada, un envasado), se corrigen con un ajuste de inventario trazable y con motivo.
6. El kardex de cualquier producto reproduce exactamente su stock y su valor.

## Artículo 5 — Cumplimiento tributario

1. Las reglas tributarias que cambian por norma (tasas, tarifas de ISC, umbrales, códigos, plazos) se configuran con vigencia; nunca se fijan en el código.
2. Una caída de SUNAT o del PSE nunca impide registrar una venta. Toda venta tiene su comprobante electrónico, salvo durante la prueba gratuita sin facturación habilitada (comprobante interno). Un comprobante rechazado queda señalado hasta que se reemite, y una venta anulada cuyo comprobante nunca fue aceptado no requiere nota de crédito.
3. Los comprobantes aceptados son inmutables; se corrigen con notas de crédito.
4. XML y CDR se conservan como copia propia durante el plazo legal.
5. Toda regla tributaria nueva o dudosa se valida con el contador antes de aprobar la spec que la usa.

## Artículo 6 — Seguridad y acceso

1. Toda acción se autoriza en el servidor según el permiso de quien la ejecuta. Ocultar un botón no es control de acceso.
2. Contraseñas, tokens y credenciales nunca se guardan en claro ni se vuelven a mostrar. La única excepción es un token de API, que se muestra una sola vez, al crearlo, para que el usuario lo copie.
3. Toda la plataforma se sirve solo por HTTPS.
4. Los cambios de accesos (roles, permisos, habilitaciones) quedan auditados.

## Artículo 7 — Arquitectura

1. **Stack:** Python 3.12, Django 5.2 LTS, PostgreSQL 16, plantillas Django + HTMX, DRF solo para la API de integración, tareas con cron. Decisiones y alternativas descartadas: `../specs/0000-Arquitectura/plan.md`.
2. **Hexagonal pragmática:** las reglas de negocio viven en un dominio de Python puro, testeable sin base de datos. Cada contexto usa a otro solo por su fachada pública, y lo verifica una herramienta automática.
3. **La base de datos es la red de seguridad, no el lugar de la lógica:** constraints, inmutabilidad y funciones atómicas refuerzan reglas que ya están en el dominio.
4. **Efectos externos** (SUNAT, email) se registran dentro de la transacción de negocio y se envían fuera de ella.
5. **Fechas de negocio** en hora de Lima.
6. **Simplicidad:** sin abstracciones, dependencias ni configuración que el MVP no necesite. Lo que se posterga se anota en la spec como fuera de alcance.

## Artículo 8 — Calidad

1. Las tareas duran como máximo 30 minutos y se hacen de a una: test primero (en rojo), código, test en verde, marcar la tarea y parar.
2. Cada regla de negocio tiene un test que la cita. Cada requisito funcional tiene al menos un escenario o un test que lo cubre.
3. Una tarea está hecha cuando sus tests pasan y el lint, el formato, el control de dependencias entre capas y el control de migraciones están en verde.
4. Una versión se publica solo con el 100 % de los escenarios `@critico` y la prueba de aislamiento en verde.
5. Al cerrar cada fase se actualiza [MEMORY.md](../MEMORY.md).

## Artículo 9 — Enmiendas

1. Solo el PO aprueba enmiendas. Se proponen por escrito con su motivo y su impacto en specs y planes existentes.
2. Versionado: **mayor** si se elimina o contradice un principio; **menor** si se agrega un principio o artículo; **parche** si se aclara la redacción sin cambiar su sentido.
3. Toda enmienda actualiza la tabla de cabecera, se registra en el historial y en `MEMORY.md`, y revisa las specs y planes afectados en el mismo cambio.

## Artículo 10 — ERP lite

1. **Lo esencial, no todo:** se construye lo que una PYME necesita para comprar, producir, vender, facturar, cobrar y conocer su utilidad. Lo propio de un ERP grande (multimoneda, contabilidad completa, reservas de stock, entregas parciales, aprobaciones en varios niveles, entre otros) queda fuera salvo que una spec aprobada lo incluya.
2. **Documentos con estados lineales:** compras, órdenes de producción y pedidos avanzan por estados en una sola dirección (p. ej. Creado ▸ Aprobado ▸ Facturado ▸ Entregado), cada paso con su acción explícita y su permiso. Lo que ya produjo efectos (stock, comprobantes) no se edita: se anula o se corrige según el artículo 4.5.
3. **Doble validación:** lo que depende de datos que cambian (el stock, un producto o un cliente activo) se valida al aprobar o preparar el documento y otra vez al ejecutar su efecto (facturar, finalizar, recibir). No se reserva stock: la segunda validación es la que manda.
4. **Maestros, no listas fijas:** los catálogos normativos (p. ej. tipos de documento de SUNAT) y las listas del negocio (p. ej. métodos de pago) son maestros mantenibles: de la plataforma si son iguales para todas las empresas, de cada empresa si cada una elige los suyos. En el código solo queda lo algorítmico (p. ej. el dígito verificador del RUC), elegible desde el maestro. Complementa el artículo 5.1.

## Historial de enmiendas

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 2026-10-10 | Ratificación inicial. Se separa de `AGENTS.md` y se consolidan los principios del PRD (RN-GEN), de la arquitectura y del flujo SDD |
| 1.2.0 | 2026-10-13 | Artículo 10 "ERP lite": alcance esencial, documentos con estados lineales, doble validación sin reservas y catálogos en maestros mantenibles; el artículo 1 define el producto como ERP lite. Pedido del PO ("estamos haciendo un ERP lite, déjalo en constitución"). Specs revisadas: 0006a y 0006b ya lo siguen; las implementadas (0004a, 0005a) ya cumplen la doble validación |
| 1.1.0 | 2026-10-10 | Excepciones explícitas tras la validación de specs: datos de plataforma para el super admin (art. 3.1); corrección por ajuste cuando la anulación falsearía el inventario (art. 4.5); comprobante interno en la prueba gratuita y tratamiento de rechazados (art. 5.2); token de API visible una sola vez (art. 6.2). Aprobada por el PO |
