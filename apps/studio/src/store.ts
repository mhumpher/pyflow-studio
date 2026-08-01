import { create } from "zustand";
import {
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
} from "@xyflow/react";
import { DEFAULT_ANNOTATION_COLOR } from "./annotations";
import type {
  AnnotationData,
  ConfigField,
  PreviewData,
  PyflowNodeData,
  RunMessage,
  SchemaMap,
  ToolDesc,
} from "./types";

let nodeSeq = 0;
let edgeSeq = 0;
let annoSeq = 0;
let lastTag: string | undefined;
let clipboard: { nodes: Node<any>[]; edges: Edge[] } | null = null;
const HISTORY_LIMIT = 60;

interface Snapshot {
  nodes: Node<any>[];
  edges: Edge[];
}

function defaultFor(field: ConfigField): unknown {
  if (field.type === "array") return [];
  if (field.type === "boolean") return false;
  if (field.type === "integer" || field.type === "number") return 0;
  if (field.type === "enum") return field.enum?.[0] ?? "";
  return "";
}

interface StoreState {
  catalog: ToolDesc[];
  nodes: Node<any>[];
  edges: Edge[];
  selectedId?: string;
  running: boolean;
  messages: RunMessage[];
  preview?: PreviewData;
  previewAnchor?: string;
  fitSignal: number;
  schemas: SchemaMap;
  functions: string[];
  currentName?: string;
  past: Snapshot[];
  future: Snapshot[];

  setCatalog: (catalog: ToolDesc[]) => void;
  setSchemas: (schemas: SchemaMap) => void;
  setFunctions: (functions: string[]) => void;
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (conn: Connection) => void;
  addNode: (tool: ToolDesc, pos: { x: number; y: number }) => void;
  addAnnotation: (pos?: { x: number; y: number }) => void;
  updateAnnotation: (id: string, patch: Partial<AnnotationData>) => void;
  loadExample: () => void;
  loadDoc: (doc: any) => void;
  clearCanvas: () => void;
  setCurrentName: (name?: string) => void;
  select: (id?: string) => void;
  toggleDisabled: (id?: string) => void;
  updateConfig: (id: string, key: string, value: unknown) => void;
  patchNode: (id: string, patch: Partial<PyflowNodeData>) => void;
  resetRun: () => void;
  setRunning: (running: boolean) => void;
  addMessage: (m: RunMessage) => void;
  setPreview: (preview?: PreviewData, anchor?: string) => void;
  takeSnapshot: (tag?: string) => void;
  undo: () => void;
  redo: () => void;
  copySelection: () => void;
  pasteClipboard: () => void;
  workflowDoc: () => unknown;
}

export const useStore = create<StoreState>((set, get) => ({
  catalog: [],
  nodes: [],
  edges: [],
  running: false,
  messages: [],
  fitSignal: 0,
  schemas: {},
  functions: [],
  past: [],
  future: [],

  setCatalog: (catalog) => set({ catalog }),
  setSchemas: (schemas) => set({ schemas }),
  setFunctions: (functions) => set({ functions }),

  onNodesChange: (changes) => {
    if (changes.some((c) => c.type === "remove")) get().takeSnapshot();
    set({ nodes: applyNodeChanges(changes, get().nodes) as Node<any>[] });
  },
  onEdgesChange: (changes) => {
    if (changes.some((c) => c.type === "remove")) get().takeSnapshot();
    set({ edges: applyEdgeChanges(changes, get().edges) });
  },
  onConnect: (conn) => {
    get().takeSnapshot();
    set({ edges: addEdge({ ...conn, id: `e${++edgeSeq}` }, get().edges) });
  },

  addNode: (tool, pos) => {
    get().takeSnapshot();
    const id = `n${++nodeSeq}`;
    const config: Record<string, unknown> = {};
    for (const f of tool.configFields) {
      config[f.name] = f.default ?? defaultFor(f);
    }
    const node: Node<any> = {
      id,
      type: "pyflow",
      position: pos,
      data: {
        toolType: tool.type,
        name: tool.name,
        inputs: tool.inputs,
        outputs: tool.outputs,
        config,
        status: "idle",
      } as PyflowNodeData,
    };
    set({ nodes: [...get().nodes, node], selectedId: id });
  },

  addAnnotation: (pos) => {
    get().takeSnapshot();
    const id = `a${++annoSeq}`;
    const node: Node<any> = {
      id,
      type: "annotation",
      position: pos ?? { x: 80 + annoSeq * 24, y: 80 + annoSeq * 24 },
      data: { kind: "annotation", text: "", color: DEFAULT_ANNOTATION_COLOR } as AnnotationData,
    };
    // Prepend so notes render behind the tool nodes.
    set({ nodes: [node, ...get().nodes], selectedId: id });
  },

  updateAnnotation: (id, patch) => {
    get().takeSnapshot(`anno:${id}:${Object.keys(patch).join(",")}`);
    set({
      nodes: get().nodes.map((n) =>
        n.id === id ? { ...n, data: { ...n.data, ...patch } } : n,
      ),
    });
  },

  loadExample: () => {
    const cat = get().catalog;
    const find = (t: string) => cat.find((c) => c.type === t);
    const input = find("input.file");
    const filter = find("prep.filter");
    const formula = find("prep.formula");
    const summarize = find("transform.summarize");
    const browse = find("output.browse");
    if (!input || !filter || !formula || !summarize || !browse) return;

    const mk = (tool: ToolDesc, pos: { x: number; y: number }, config: Record<string, unknown>) => ({
      id: `n${++nodeSeq}`,
      type: "pyflow",
      position: pos,
      data: {
        toolType: tool.type,
        name: tool.name,
        inputs: tool.inputs,
        outputs: tool.outputs,
        config,
        status: "idle" as const,
      },
    });

    const n1 = mk(input, { x: 20, y: 140 }, {
      path: "examples/data/customers.csv",
      format: "csv",
      has_header: true,
      delimiter: ",",
    });
    const n2 = mk(filter, { x: 250, y: 140 }, { expression: '[status] == "active"' });
    const n3 = mk(formula, { x: 480, y: 140 }, {
      formulas: [{ output: "revenue", expression: "Round([spend] * 1.1, 2)", type: "" }],
    });
    const n4 = mk(summarize, { x: 710, y: 140 }, {
      group_by: ["region"],
      aggregations: [
        { field: "revenue", func: "sum", output: "total_revenue" },
        { field: "id", func: "count", output: "customers" },
      ],
    });
    const n5 = mk(browse, { x: 940, y: 110 }, {});
    const edge = (s: string, sh: string, t: string): Edge => ({
      id: `e${++edgeSeq}`,
      source: s,
      target: t,
      sourceHandle: sh,
      targetHandle: "in",
    });

    get().takeSnapshot();
    set({
      nodes: [n1, n2, n3, n4, n5] as Node<any>[],
      edges: [
        edge(n1.id, "out", n2.id),
        edge(n2.id, "true", n3.id),
        edge(n3.id, "out", n4.id),
        edge(n4.id, "out", n5.id),
      ],
      selectedId: n4.id,
      fitSignal: get().fitSignal + 1,
    });
  },

  loadDoc: (doc: any) => {
    const cat = get().catalog;
    let maxN = 0;
    let maxE = 0;
    const nodes: Node<any>[] = (doc.nodes ?? []).map((n: any) => {
      const tool = cat.find((t) => t.type === n.type);
      const m = /^n(\d+)$/.exec(n.id);
      if (m) maxN = Math.max(maxN, parseInt(m[1], 10));
      return {
        id: n.id,
        type: "pyflow",
        position: n.position ?? { x: 0, y: 0 },
        data: {
          toolType: n.type,
          name: tool?.name ?? n.type,
          inputs: tool?.inputs ?? [],
          outputs: tool?.outputs ?? [],
          config: n.config ?? {},
          status: "idle" as const,
          disabled: n.disabled ?? false,
        },
      };
    });
    const edges: Edge[] = (doc.edges ?? []).map((e: any) => {
      const m = /^e(\d+)$/.exec(e.id);
      if (m) maxE = Math.max(maxE, parseInt(m[1], 10));
      return {
        id: e.id,
        source: e.source.node,
        target: e.target.node,
        sourceHandle: e.source.anchor,
        targetHandle: e.target.anchor,
      };
    });
    let maxA = 0;
    const annotations: Node<any>[] = (doc.annotations ?? []).map((a: any) => {
      const m = /^a(\d+)$/.exec(a.id ?? "");
      if (m) maxA = Math.max(maxA, parseInt(m[1], 10));
      return {
        id: a.id,
        type: "annotation",
        position: a.position ?? { x: 0, y: 0 },
        data: {
          kind: "annotation",
          text: a.text ?? "",
          color: a.color ?? DEFAULT_ANNOTATION_COLOR,
        } as AnnotationData,
      };
    });
    nodeSeq = Math.max(nodeSeq, maxN);
    edgeSeq = Math.max(edgeSeq, maxE);
    annoSeq = Math.max(annoSeq, maxA);
    lastTag = undefined;
    set({
      // Annotations first so they render behind the tool nodes.
      nodes: [...annotations, ...nodes],
      edges,
      selectedId: undefined,
      preview: undefined,
      messages: [],
      past: [],
      future: [],
      fitSignal: get().fitSignal + 1,
    });
  },

  clearCanvas: () => {
    get().takeSnapshot();
    set({ nodes: [], edges: [], selectedId: undefined, preview: undefined, messages: [], currentName: undefined });
  },

  setCurrentName: (name) => set({ currentName: name }),

  select: (id) => set({ selectedId: id }),

  toggleDisabled: (id) => {
    const { nodes, selectedId } = get();
    const target = new Set(
      id ? [id] : nodes.filter((n) => n.selected).map((n) => n.id),
    );
    if (target.size === 0 && selectedId) target.add(selectedId);
    if (target.size === 0) return;
    get().takeSnapshot();
    // If any target is currently enabled, disable them all; otherwise enable all.
    const disable = nodes.some(
      (n) => target.has(n.id) && !(n.data as PyflowNodeData).disabled,
    );
    set({
      nodes: nodes.map((n) =>
        target.has(n.id) ? { ...n, data: { ...n.data, disabled: disable } } : n,
      ),
    });
  },

  updateConfig: (id, key, value) => {
    get().takeSnapshot(`cfg:${id}:${key}`);
    set({
      nodes: get().nodes.map((n) =>
        n.id === id
          ? { ...n, data: { ...n.data, config: { ...n.data.config, [key]: value } } }
          : n,
      ),
    });
  },

  patchNode: (id, patch) =>
    set({
      nodes: get().nodes.map((n) =>
        n.id === id ? { ...n, data: { ...n.data, ...patch } } : n,
      ),
    }),

  resetRun: () =>
    set({
      messages: [],
      nodes: get().nodes.map((n) => ({
        ...n,
        data: { ...n.data, status: "idle", rows: undefined, anchorRows: undefined, cached: undefined },
      })),
    }),

  setRunning: (running) => set({ running }),
  addMessage: (m) => set({ messages: [...get().messages, m] }),
  setPreview: (preview, anchor) => set({ preview, previewAnchor: anchor }),

  takeSnapshot: (tag) => {
    // Coalesce consecutive edits with the same tag (e.g. typing in one field) so
    // they collapse into a single undo step.
    if (tag && tag === lastTag) return;
    lastTag = tag;
    const { nodes, edges, past } = get();
    const next = [...past, { nodes, edges }];
    if (next.length > HISTORY_LIMIT) next.shift();
    set({ past: next, future: [] });
  },

  undo: () => {
    const { past, future, nodes, edges } = get();
    if (past.length === 0) return;
    lastTag = undefined;
    const prev = past[past.length - 1];
    set({
      past: past.slice(0, -1),
      future: [...future, { nodes, edges }],
      nodes: prev.nodes,
      edges: prev.edges,
      selectedId: undefined,
      preview: undefined,
    });
  },

  redo: () => {
    const { past, future, nodes, edges } = get();
    if (future.length === 0) return;
    lastTag = undefined;
    const next = future[future.length - 1];
    set({
      future: future.slice(0, -1),
      past: [...past, { nodes, edges }],
      nodes: next.nodes,
      edges: next.edges,
      selectedId: undefined,
      preview: undefined,
    });
  },

  copySelection: () => {
    const { nodes, edges } = get();
    const selected = nodes.filter((n) => n.selected);
    if (selected.length === 0) return;
    const ids = new Set(selected.map((n) => n.id));
    clipboard = {
      nodes: selected.map((n) => ({
        ...n,
        data: { ...n.data, config: JSON.parse(JSON.stringify((n.data as PyflowNodeData).config ?? {})) },
      })),
      edges: edges.filter((e) => ids.has(e.source) && ids.has(e.target)),
    };
  },

  pasteClipboard: () => {
    if (!clipboard || clipboard.nodes.length === 0) return;
    get().takeSnapshot();
    const idMap = new Map<string, string>();
    const offset = 40;
    const newNodes: Node<any>[] = clipboard.nodes.map((n) => {
      const newId = `n${++nodeSeq}`;
      idMap.set(n.id, newId);
      return {
        ...n,
        id: newId,
        selected: true,
        position: { x: n.position.x + offset, y: n.position.y + offset },
        data: {
          ...n.data,
          config: JSON.parse(JSON.stringify((n.data as PyflowNodeData).config ?? {})),
          status: "idle",
          rows: undefined,
          anchorRows: undefined,
          cached: undefined,
        },
      };
    });
    const newEdges: Edge[] = clipboard.edges.map((e) => ({
      ...e,
      id: `e${++edgeSeq}`,
      source: idMap.get(e.source) ?? e.source,
      target: idMap.get(e.target) ?? e.target,
    }));
    set({
      nodes: [...get().nodes.map((n) => ({ ...n, selected: false })), ...newNodes],
      edges: [...get().edges, ...newEdges],
      selectedId: newNodes[newNodes.length - 1]?.id,
    });
  },

  workflowDoc: () => {
    const { nodes, edges } = get();
    return {
      pyflow_version: "1.0",
      id: "current",
      name: "Studio workflow",
      nodes: nodes
        .filter((n) => n.type !== "annotation")
        .map((n) => ({
          id: n.id,
          type: (n.data as PyflowNodeData).toolType,
          position: { x: n.position.x, y: n.position.y },
          config: (n.data as PyflowNodeData).config,
          disabled: (n.data as PyflowNodeData).disabled ?? false,
        })),
      edges: edges.map((e) => ({
        id: e.id,
        source: { node: e.source, anchor: e.sourceHandle || "out" },
        target: { node: e.target, anchor: e.targetHandle || "in" },
      })),
      annotations: nodes
        .filter((n) => n.type === "annotation")
        .map((n) => ({
          id: n.id,
          position: { x: n.position.x, y: n.position.y },
          text: (n.data as AnnotationData).text,
          color: (n.data as AnnotationData).color,
        })),
    };
  },
}));

// Dev/E2E affordance: expose the store for inspection from the console.
if (typeof window !== "undefined") {
  (window as unknown as { pfStore: typeof useStore }).pfStore = useStore;
}
