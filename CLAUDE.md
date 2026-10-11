# CLAUDE.md — Entrada de contexto para Claude Code

Lee y respeta estrictamente en todo momento el orden de precedencia y las directrices definidas en los siguientes archivos:

1. @docs/constitution.md (Principios no negociables. Gana sobre todo lo demás).
2. @AGENTS.md (Guía de trabajo SDD, ciclo de vida de specs, identificadores EARS, formato Gherkin y reglas de entorno).
3. @MEMORY.md (Estado actual de las specs, decisiones tomadas y pendientes).

## Comandos rápidos de verificación
- **Linter & Formato:** `.venv/bin/ruff check` && `.venv/bin/ruff format --check`
- **Imports:** `.venv/bin/lint-imports`
- **Tests:** `.venv/bin/pytest`
- **Migraciones:** `.venv/bin/python manage.py makemigrations --check`
