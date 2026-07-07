# Contributing to Pyflow

Thanks for your interest in contributing! Pyflow is an early-stage, community-built project — issues,
ideas, and pull requests are all welcome.

## Getting set up

See [DEVELOPMENT.md](DEVELOPMENT.md) for the full setup. In short:

```bash
python -m venv .venv && . .venv/Scripts/activate   # (or source .venv/bin/activate)
pip install -e ".[dev]"
cd apps/studio && npm install && npm run build
pyflow studio
```

## Project layout

- `packages/engine` — the pure-Python execution engine (DAG, scheduler, tools, type system, cache)
- `packages/sdk` — the stable, public surface for authoring custom tools
- `packages/server` — the FastAPI app (REST + WebSocket) and the `pyflow` CLI
- `apps/studio` — the React + React Flow frontend
- `docs/` — the specification (start with `docs/00-vision-and-scope.md`)

## Adding a tool

Most contributions are new tools. A tool is a small class in `packages/engine/pyflow_engine/tools/`
that declares anchors + a Pydantic config and implements `build()` (and optionally `run()` for side
effects or data-dependent output). See existing tools and [docs/05-tool-sdk.md](docs/05-tool-sdk.md).
Register it in `packages/engine/pyflow_engine/registry.py`. No frontend change is usually needed — the
config panel is generated from the config schema.

## Style & checks

- **Python:** `ruff` for lint/format; type hints throughout (`mypy`). Match the surrounding code.
- **TypeScript/React:** keep components small and typed; follow the existing patterns in `apps/studio`.
- Prefer small, focused pull requests with a clear description of the behavior change.

## Tests

```bash
pytest                       # engine + tool tests
cd apps/studio && npm run build   # ensure the frontend compiles
```

Please add or update tests for behavior changes where practical.

## Reporting bugs & requesting features

Open a GitHub issue with steps to reproduce (a minimal `.pyflow` file helps) and your OS/Python/Node
versions. For anything security-related, see [SECURITY.md](SECURITY.md) instead of a public issue.

## Licensing of contributions

By submitting a contribution, you agree that it is licensed under the project's
[Apache-2.0](LICENSE) license.
