# 06 — Frontend / GUI

The Studio frontend is a React + TypeScript app built on **React Flow** for the canvas. It is a pure
view/controller over the server and engine — it renders state and issues commands, but performs no data
logic. This document specifies layout, interactions, and component structure.

---

## 1. Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Toolbar:  [Run ▶] [Stop ■] [Save] [Undo/Redo]   Workflow: Customer cleanup │
├───────────────┬──────────────────────────────────────┬─────────────────────┤
│  TOOL PALETTE │             CANVAS                    │   CONFIG PANEL       │
│  (searchable) │   [Input]──[Filter]──┐                │  (selected node)     │
│               │                       [Join]──[Output] │                     │
│  ▸ Input/Out  │   [Lookup]───────────┘                │  fields, options…    │
│  ▸ Preparation│                                        │                     │
│  ▸ Join       │            (pan / zoom / minimap)      │                     │
│  ▸ Transform  │                                        │                     │
│  ▸ Parse      │                                        │                     │
├───────────────┴──────────────────────────────────────┴─────────────────────┤
│  RESULTS PANEL:  [Data grid] [Profile] [Messages] [Metadata]   — node "Join" │
│   id | name        | region | revenue     ▸ 480,123 rows · 9 cols · 812 ms   │
└──────────────────────────────────────────────────────────────────────────┘
```

Four regions: **Tool palette** (left), **Canvas** (center), **Config panel** (right, contextual to
selection), **Results panel** (bottom, contextual to selection). All are resizable/collapsible.

## 2. Tool palette (left)

- Categorized, searchable list of all registered tools (fetched from `GET /tools`).
- Search matches name, category, and synonyms ("dedupe" → Unique, "pivot" → Cross Tab).
- Drag a tool onto the canvas to create a node; or click to insert connected to the current selection.
- Favorites/recent section; plugin tools appear under their declared category with a badge.

## 3. Canvas (center) — React Flow

- **Nodes**: custom React Flow node showing icon, title, input/output anchors, and a **status badge**
  (idle / queued / running / done / error) plus a record count after a run.
- **Anchors**: multi-output tools (Filter, Join, Unique) show clearly labeled ports.
- **Edges**: bezier connections; hovering shows the flowing schema (field count/types); invalid
  connections are rejected with a reason tooltip.
- **Interactions**: pan, zoom, box-select, multi-select, copy/paste, align/distribute, minimap,
  fit-to-view. Drag from an output anchor to empty canvas to open a **quick-add** tool menu.
- **Containers/annotations**: draw comment boxes and collapsible tool groups.
- **Undo/redo**: full document history (see §7). **Keyboard**: Del, Ctrl+C/V/Z/Y, Ctrl+S, F5 (run).
- **Live run overlay**: nodes animate through statuses as WebSocket events arrive; the active edge/branch
  highlights; errors mark the node red with an inline message.

## 4. Config panel (right)

- Renders the selected node's **auto-generated form** from its config JSON Schema (see
  [Tool SDK §2](05-tool-sdk.md)).
- **Field pickers** are populated from the node's *actual incoming schema* (design-time schema pass), so
  the analyst selects real columns, not free text.
- **Formula editor** (Monaco) offers autocomplete for incoming fields + the function library, inline
  type checks, and a **live preview** evaluated on a cached sample.
- Changes are debounced → `PATCH` the node config → re-validate → mark the node (and descendants) stale.
- Shows the node's **output field list** (post-transform schema) and any config validation errors inline.

## 5. Results panel (bottom)

Contextual to the selected node; tabs:

| Tab | Content |
| --- | --- |
| **Data** | Virtualized grid of a bounded sample of the node's output (TanStack Virtual). Sort/scroll; type-aware cell rendering; null highlighting. |
| **Profile** | Per-column profiling: type, % null, distinct count, min/max/mean, and a mini value-distribution histogram — Alteryx "Browse"-style. |
| **Messages** | The tool's run messages (info/warn/error), e.g. "12 rows failed date parse → null". |
| **Metadata** | The output schema as a table: field, type, nullable, description, source. |

Previews are **sampled server-side** — the browser never receives full datasets (see
[Backend API](07-backend-api.md)).

## 6. Core user flows

**Build & run**
1. Drag **Input Data**, pick a CSV → schema appears; Data tab shows a preview.
2. Drag **Filter**, connect, type a formula → True/False previews update on sample.
3. Add **Join** to a lookup, **Summarize** by group, **Output Data** to Excel.
4. **Run ▶** → nodes stream through statuses; click any node to inspect its Data/Profile.

**Iterate fast**
- Edit one node's config → only that node and its descendants recompute (engine cache); previews refresh.

**Debug**
- A red node shows its error message; open **Messages**; fix config; re-run just that branch.

## 7. State management

Two state layers (Zustand stores):

- **Document state** — the workflow (nodes, edges, configs, annotations). Source of truth for save;
  mutations produce undo/redo entries and sync to the server (`PATCH`/WS).
- **View/session state** — selection, viewport, panel sizes, run status per node, cached preview handles.
  Not persisted to the `.pyflow` file (except positions, which are document state).

Undo/redo is implemented as an inverse-command stack over document mutations. Autosave to the server
session on a debounce; explicit **Save** writes the `.pyflow` file.

## 8. Component tree (sketch)

```
<App>
├─ <Toolbar />                       run/stop/save/undo, workflow name
├─ <WorkspaceLayout>                 resizable panes
│  ├─ <ToolPalette />                categories, search, drag sources
│  ├─ <FlowCanvas>                   React Flow provider
│  │  ├─ <PyflowNode />              custom node (anchors, status, count)
│  │  ├─ <PyflowEdge />              schema-aware edge
│  │  ├─ <QuickAddMenu />            drag-to-empty tool insert
│  │  └─ <Minimap /> <Controls />
│  ├─ <ConfigPanel>                  contextual to selection
│  │  ├─ <SchemaForm />              JSON-Schema → form
│  │  ├─ <FieldPicker /> <FormulaEditor(Monaco) />
│  │  └─ <OutputSchemaList />
│  └─ <ResultsPanel>                 contextual to selection
│     ├─ <DataGrid /> (virtualized)
│     ├─ <ColumnProfile />
│     ├─ <MessagesList />
│     └─ <MetadataTable />
└─ <RunStatusProvider />             WebSocket → per-node status
```

## 9. Accessibility, theming, i18n

- **Keyboard-navigable** canvas and panels; visible focus; ARIA roles on nodes/edges/controls.
- **Light/dark themes** via CSS variables; high-contrast option.
- **Internationalization** scaffolding from day one (externalized strings); English first.
- Respect `prefers-reduced-motion` for run animations.

## 10. Performance targets (UI)

- Smooth pan/zoom with **500+ node** workflows (React Flow virtualization; memoized nodes).
- Data grid renders a **100k-row sample** at 60 fps via row virtualization.
- Config edits reflect in previews within a few hundred ms on cached samples.
- Preview payloads are capped (default 1–10k rows) and paged; full data stays server-side.

## 11. Explicit non-goals (frontend)

- No client-side data processing beyond rendering samples.
- No bespoke charting engine at MVP (Reporting tools render server-side later).
- No offline PWA mode at MVP (the local server is always present).
