# AGENTS.md — Guía de trabajo para agentes y personas

Antes de cualquier tarea, lee y respeta:

1. **[docs/constitution.md](docs/constitution.md):** principios no negociables. Gana sobre todo lo demás.
2. **[MEMORY.md](MEMORY.md):** estado actual: fase de cada spec, decisiones tomadas y pendientes.
3. **La skill `sdd`** ([.agent/skills/sdd/SKILL.md](.agent/skills/sdd/SKILL.md)): plantillas de spec, plan y tareas.

## 1. Cómo trabajar

- Identifica en qué fase está la spec afectada (ver `MEMORY.md`) y trabaja solo en esa fase. Para avanzar, pide la aprobación del PO (constitución, art. 2).
- Si el pedido no está en ninguna spec, propón primero el cambio en la spec; no escribas código.
- Si falta una decisión, no la inventes: regístrala como `[NECESITA ACLARACIÓN]` en la spec y pregunta.
- Al cerrar una fase, actualiza `MEMORY.md`.

## 2. Estructura

```
docs/constitution.md              ← principios (fase 1 de SDD)
AGENTS.md                         ← esta guía
CLAUDE.md                         ← importa docs/constitution.md, AGENTS.md y MEMORY.md
MEMORY.md                         ← estado y decisiones
.agent/                           ← agentes, comandos y skills compartidos por las herramientas de IA
.claude → .agent                  ← enlace simbólico: Claude Code solo lee .claude/
PRD.md                            ← visión, alcance MVP, RN-GEN, métricas, preguntas Q1…Qn
specs/
├── 0000-Arquitectura/plan.md     ← decisiones técnicas transversales (ADR, capas, tenancy, persistencia)
└── NNNNx-Modulo-nombre/          ← una carpeta por spec: épica de 4 dígitos + parte (a, b, c…) + módulo + nombre
                                    (p. ej. 0002a-Catalogo-productos … 0008b-Finanzas-resultados-reportes; 0002d-Catalogo-proveedores se agregó el 2026-10-10)
    ├── spec.md                   ← QUÉ y POR QUÉ: historias, RF en EARS, casos límite, dudas. Sin stack
    ├── plan.md                   ← CÓMO: modelo de datos, casos de uso, algoritmos, decisiones, tests
    ├── tasks.md                  ← tareas de ≤ 30 min con su RF y su "hecho cuando" (solo con plan aprobado)
    └── features/*.feature        ← escenarios Gherkin: criterio de aceptación ejecutable (pytest-bdd)
```

Estado de cada spec (en su encabezado): `borrador` → `aprobada` → `implementada`.

## 3. Identificadores

| Elemento | Formato | Ejemplo |
|---|---|---|
| Spec | Carpeta `NNNNx-Modulo-nombre`; se cita por `NNNNx` y la épica por `NNNN`; alias `E0N` / `E0Nx` en tags | `0006b-Ventas-registro-venta` = `0006b` = `E06b` |
| Historia de usuario | `H<n>` (por spec) | `H3` |
| Requisito funcional | `RF-<MÓDULO>-<NN>` en EARS, en `spec.md` | `RF-TEN-07` |
| Requisito no funcional | `RNF-<MÓDULO>-<NN>` | `RNF-FAC-01` |
| Caso de uso | `UC-<MÓDULO>-<NN>` | `UC-VEN-05` |
| Regla de negocio | `RN-<MÓDULO>-<NN>`, citada entre paréntesis en el RF que la implementa; transversales `RN-GEN-NN` en el PRD | `RN-INV-04` |
| Módulos | `TEN`, `CAT`, `INV`, `COM`, `PRD`, `VEN`, `FAC`, `FIN` | — |

**Requisitos en EARS (español):**
- `CUANDO <evento>, EL SISTEMA <respuesta>.`
- `SI <condición no deseada>, ENTONCES EL SISTEMA <respuesta>.`
- `MIENTRAS <estado>, EL SISTEMA <respuesta>.`
- `EL SISTEMA <comportamiento permanente>.`

Cada RF es verificable: nada de "rápido" o "fácil" sin un criterio medible.

**Tags Gherkin:** `@E0N` · `@E0Nx` (la parte de la épica) · `@UC-…` · `@RF-…` (obligatorio: los RF que el escenario verifica; un RF sin escenario debe tener un test que lo cite en el plan §7) · `@RN-…` (obligatorio si el escenario prueba una regla) · `@critico` (bloquea el release) · `@borde` · `@mvp` / `@r2` · `@pendiente-qN` (depende de la pregunta N del PRD; no se ejecuta hasta resolverla) · `@borrador` (escenario de una spec o enmienda sin aprobar; no se ejecuta hasta su aprobación, y se quita al implementarla). Idioma: `# language: es`.

## 4. Entorno y comandos de verificación

```
docker run -d --name illumi-pg -e POSTGRES_USER=illumi -e POSTGRES_PASSWORD=illumi \
  -e POSTGRES_DB=illumi -p 54320:5432 postgres:16   # base de desarrollo en localhost:54320
python3 -m venv .venv && .venv/bin/pip install -e . pytest pytest-django pytest-bdd hypothesis ruff import-linter   # -e . instala django y djangorestframework
.venv/bin/python manage.py migrate
```

Despliegue local de prueba (gunicorn + PostgreSQL + cron): `docker compose up -d --build` → http://localhost:8020.

`ruff check` · `ruff format --check` · `lint-imports` · `pytest` (o `pytest -k E01a` por spec) · `python manage.py makemigrations --check`.

## 5. Idioma y estilo

- Specs, mensajes de usuario y commits en español.
- En el código, el dominio va en español (`Venta`, `RegistrarCompra`) y lo técnico estándar en inglés (`repository`, `middleware`).
