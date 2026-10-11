---
name: sdd
description: Flujo Spec-Driven Development de Illumi-CRM (constitución → spec → plan → tareas → implementación). Usar al crear o modificar una spec, un plan o tareas en specs/NNN-nombre/, o antes de implementar cualquier funcionalidad.
---
# Spec-Driven Development (SDD)
## Flujo
Constitución → Spec → Clarificación → Plan → Tareas → Implementación → Validación →
Cambio.
- La constitución vive en `docs/constitution.md`. Si una spec la contradice, gana la
constitución; se enmienda según su artículo 9.
- Nunca pases a la siguiente fase sin la aprobación explícita del usuario.
- La spec manda: si algo no está en la spec, no se implementa. Si falta una decisión,
para y pregunta.
- Un cambio de requisitos se hace primero en la spec, luego en el plan y las tareas, y
por último en el código.
- Cada spec vive en su carpeta: `specs/NNNNx-Modulo-nombre/` (p. ej. `specs/0002a-Catalogo-productos/`) con `spec.md`, `plan.md`,
`tasks.md` y `features/*.feature` (escenarios Gherkin en español, criterio de aceptación
ejecutable con `pytest-bdd`). Los principios están en `docs/constitution.md` y la guía de trabajo en `AGENTS.md`.
- Al terminar cada fase, actualiza `MEMORY.md`.
## Plantilla de spec (spec.md)
```
# Spec NNNNx — <Módulo>: <nombre de la funcionalidad>
Estado: borrador | aprobada | implementada
## Contexto y objetivo
<Qué problema resuelve y por qué merece la pena. Un párrafo.>
## Usuarios / actores
<Quién lo usa.>
## Historias de usuario
- H1: Como <rol> quiero <acción> para <beneficio>.
## Definiciones
<Opcional: solo si hay términos, fórmulas o tablas que puedan interpretarse de varias formas.>
## Requisitos funcionales (criterios de aceptación en EARS)
- RF-<MÓD>-01: CUANDO <evento>, EL SISTEMA <respuesta> (salida/resultado esperado).
- RF-<MÓD>-02: SI <condición no deseada>, ENTONCES EL SISTEMA <respuesta>.
- RF-<MÓD>-03: MIENTRAS <estado>, EL SISTEMA <respuesta>.
- RF-<MÓD>-04: EL SISTEMA <comportamiento permanente>.
## Requisitos no funcionales
<Solo los que apliquen: rendimiento, seguridad, plataformas, idioma...>
## Casos límite
<Vacíos, duplicados, datos corruptos, límites, concurrencia...>
## Fuera de alcance
<Lo que explícitamente NO se hace en esta iteración.>
## Criterios de finalización
<Ej.: todos los RF con test en verde + demo manual del flujo principal.>
## Dudas abiertas
- [NECESITA ACLARACIÓN] <duda>
```
- `<MÓD>` es el módulo de la spec (`TEN`, `CAT`, `INV`, `COM`, `PRD`, `VEN`, `FAC`, `FIN`), así cada RF es único en todo el proyecto.
- Si un RF implementa una regla de negocio, la cita entre paréntesis al final: `(RN-INV-04)`.
- Los RF se pueden agrupar con subtítulos `### UC-<MÓD>-NN <nombre>`.
La spec describe el QUÉ y el POR QUÉ. Nada de stack, arquitectura ni nombres de archivos.
## Requisitos en EARS (en español)
- RF-x: CUANDO <evento>, EL SISTEMA <respuesta>.
- RF-x: SI <condición no deseada>, ENTONCES EL SISTEMA <respuesta>.
- RF-x: MIENTRAS <estado>, EL SISTEMA <respuesta>.
- RF-x: EL SISTEMA <comportamiento permanente>.
Cada RF debe ser verificable: nada de "rápido", "intenso" o "bonito" sin un criterio
medible.
## Plan (plan.md)
Archivos y responsabilidades · Funciones puras (con "hoy" como parámetro) · Algoritmo en
pseudocódigo · Interfaz · Decisiones justificadas con su alternativa descartada ·
Estrategia de tests con `pytest` (unitario de dominio, casos de uso con fakes,
integración con PostgreSQL, aceptación con `pytest-bdd`). Indica qué RF cubre cada parte.
## Tareas (tasks.md)
```
- [ ] **Tn. <Descripción>.** RF-x, RF-y
 - Hecho cuando: <comprobación verificable>.
```
Máximo 20-30 min por tarea, en orden de dependencia. Si salen más de 10, propón dividir
la spec.
## Implementación
Una sola tarea cada vez: tests primero (en rojo), después el código, `pytest` en
verde, marcar la tarea y parar.