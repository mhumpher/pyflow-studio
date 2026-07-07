# 09 — Non-Functional Requirements

Cross-cutting requirements that apply to all phases: performance, scalability, security, reliability,
testing, packaging, observability, and licensing.

---

## 1. Performance

| Aspect | Target |
| --- | --- |
| Interactive edit → preview | < ~500 ms on a cached upstream sample |
| Incremental re-run | Only edited node + descendants recompute (cache hit for the rest) |
| Throughput | Beat a pandas-equivalent workflow on the same hardware (Polars/DuckDB) |
| Canvas | Smooth pan/zoom at 500+ nodes; 60 fps grid on 100k-row samples |
| Startup | `pyflow studio` to interactive canvas in a few seconds |
| Preview payloads | Bounded (default 1–10k rows), paginated, Arrow-encoded |

**Principle:** minimize data crossing process boundaries — push down projection/predicate to readers,
keep data columnar/lazy, and sample for the UI.

## 2. Scalability

| Data scale | Guarantee |
| --- | --- |
| ≤ RAM | Full in-memory Polars |
| > RAM, single node | Streaming (Polars) + out-of-core (DuckDB), spill to disk, **no OOM** |
| Cluster | Dask/Ray backend (Phase 3), partitioned execution |
| In-warehouse | Push compute down (DuckDB → Ibis-style multi-backend later) |

Memory ceilings are configurable; the engine prefers spilling over failing. Workflows scale from a
laptop to a cluster **without tool rewrites** (the `Frame` abstraction).

## 3. Security & privacy

- **Local-first / private by default:** nothing leaves the machine unless the user connects a source;
  telemetry is **opt-in** only.
- **Network binding:** MVP binds to `127.0.0.1`; a per-session token guards REST/WS against other local
  processes.
- **Filesystem allow-list:** all file access is confined to a configured workspace root with
  path-traversal protection.
- **Secrets:** DB/cloud credentials live in a local secret store, **never** sent to the browser; tools
  read them server-side via `ctx.secret()`.
- **User-code sandboxing (Python/SQL tools):** execute in a constrained subprocess with resource limits
  (CPU/mem/time), no ambient network by default, and no access outside the workspace/allow-list. This is
  a **prerequisite** for shipping the Developer tools (Phase 2).
- **Plugins:** third-party tools run in-process at MVP (trusted-install model); signed plugins +
  optional isolation land with the marketplace (Phase 4). Document the trust model clearly.
- **Multi-user (Phase 4):** pluggable auth (OIDC/token), per-workflow RBAC, audit logging, secret scoping.
- **Dependency hygiene:** SBOM, pinned deps, automated vulnerability scanning in CI.

## 4. Reliability & correctness

- **Determinism:** given the same inputs + config, a workflow produces the same output (modulo explicitly
  random tools seeded via config).
- **Reproducibility:** GUI and headless runs share one engine code path (see [Architecture §7](01-architecture.md)).
- **Graceful failure:** a failing node halts its branch only; independent branches continue; errors are
  structured and surfaced per node.
- **Data integrity:** exact numerics via a decimal/money type; explicit, centralized type-coercion rules;
  configurable bad-data handling (error / warn+null / drop).
- **Crash safety:** autosave + session cache allow recovery of an in-progress workflow.

## 5. Testing strategy

| Layer | Approach |
| --- | --- |
| **Tool unit tests** | `pyflow_sdk.testing.run_tool` — schema inference, happy path, nulls/empty, type errors, large-input smoke |
| **Engine** | Scheduling, cache/incremental correctness, cancellation, backend parity (same result on Polars vs DuckDB) |
| **Golden workflows** | Representative `.pyflow` files run headless; outputs diffed against fixtures |
| **Property-based** | `hypothesis` for expressions/type coercions |
| **API contract** | Schema-validated request/response; generated client kept in sync |
| **E2E** | Playwright: build a workflow in the UI, run it, assert grid/profile/messages |
| **Performance** | Benchmarks on sized datasets (1 GB / 10 GB / 50 GB) tracked over time to catch regressions |

CI runs unit + engine + golden + contract on every PR; E2E + perf on a schedule/nightly.

## 6. Packaging & distribution

- **Install:** `pip install pyflow-studio` (or the final name) ships engine + server + built frontend;
  `pyflow studio` launches locally. `pyflow-sdk` is a separate lightweight dependency for tool authors.
- **Optional extras:** heavy stacks are extras/plugins (`pip install pyflow-studio[ml,spatial,dask]`) so
  the core stays lean.
- **Cross-platform:** Windows, macOS, Linux (Python 3.11+). CI matrix across all three.
- **Desktop (Phase 4):** pywebview/Tauri shell bundling Python + frontend for a one-click installer.
- **Reproducible builds:** locked dependencies; wheels published to PyPI; the frontend is pre-built into
  the server wheel (users don't need Node).

## 7. Observability

- **Structured logging** (JSON) server- and engine-side with run/session/node correlation ids.
- **Run metrics:** per-node rows, duration, cache hit/miss, peak memory, backend used — surfaced in the UI
  and exportable.
- **Health/introspection:** `/healthz`, engine version, loaded tool catalog, active backend.
- **Optional OpenTelemetry** traces for server deployments (Phase 4).
- **Opt-in, anonymized** usage telemetry only; off by default; clearly documented.

## 8. Maintainability & DX

- **SDK/engine separation** with a semver-stable SDK (see [Tool SDK §9](05-tool-sdk.md)).
- **Typed everywhere:** mypy (Python), strict TypeScript; Pydantic models as the single source of truth
  for config schemas → UI.
- **Lint/format gates:** ruff/black + eslint/prettier via pre-commit and CI.
- **Docs-as-code:** this spec lives with the code; tool docs generated from `Tool` metadata.
- **Config migrations:** tool `version` + `migrate()` keep old `.pyflow` files loadable.

## 9. Accessibility & internationalization

- WCAG-minded: keyboard-navigable canvas/panels, focus management, ARIA roles, high-contrast theme,
  `prefers-reduced-motion` support.
- i18n scaffolding from day one (externalized strings); English first.

## 10. Licensing & governance

- **License:** intended **Apache-2.0** (permissive + patent grant); MIT is the fallback. Decide before
  first public release.
- **Contribution:** CLA/DCO, code of conduct, contribution guide, semantic-versioned releases.
- **Third-party licenses:** track and vet dependency licenses (avoid copyleft in the core that would
  restrict the intended license).
- **Trademark/name:** resolve the `pyflow` PyPI/name collision (see [README](../README.md)) before publishing.

---

## Requirements summary matrix

| NFR | MVP target | Long-term |
| --- | --- | --- |
| Performance | < 500 ms previews; beat pandas | Sustained on 50 GB+; cluster scale |
| Scale | Out-of-core single node | Distributed + in-warehouse pushdown |
| Security | Local, allow-listed FS, session token | Sandboxed user code, auth/RBAC, signed plugins |
| Reliability | Deterministic, branch-isolated errors | Crash recovery, audit, lineage |
| Testing | Unit + engine + golden + basic E2E | Perf regression tracking, backend parity suite |
| Packaging | `pip install`, cross-platform | Desktop installer, plugin marketplace |
| Observability | Structured logs + run metrics | OTel traces, run history UI |
