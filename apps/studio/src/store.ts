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
import type {
  ConfigField,
  PreviewData,
  PyflowNodeData,
  RunMessage,
  SchemaMap,
  ToolDesc,
} from "./types";

let nodeSeq = 0;
let edgeSeq = 0;

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

  setCatalog: (catalog: ToolDesc[]) => void;
  setSchemas: (schemas: SchemaMap) => void;
  setFunctions: (functions: string[]) => void;
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (conn: Connection) => void;
  addNode: (tool: ToolDesc, pos: { x: number; y: number }) => void;
  loadExample: () => void;
  clearCanvas: () => void;
  select: (id?: string) => void;
  updateConfig: (id: string, key: string, value: unknown) => void;
  patchNode: (id: string, patch: Partial<PyflowNodeData>) => void;
  resetRun: () => void;
  setRunning: (running: boolean) => void;
  addMessage: (m: RunMessage) => void;
  setPreview: (preview?: PreviewData, anchor?: string) => void;
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

  setCatalog: (catalog) => set({ catalog }),
  setSchemas: (schemas) => set({ schemas }),
  setFunctions: (functions) => set({ functions }),

  onNodesChange: (changes) =>
    set({ nodes: applyNodeChanges(changes, get().nodes) as Node<any>[] }),
  onEdgesChange: (changes) =>
    set({ edges: applyEdgeChanges(changes, get().edges) }),
  onConnect: (conn) =>
    set({ edges: addEdge({ ...conn, id: `e${++edgeSeq}` }, get().edges) }),

  addNode: (tool, pos) => {
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

  clearCanvas: () => set({ nodes: [], edges: [], selectedId: undefined, preview: undefined, messages: [] }),

  select: (id) => set({ selectedId: id }),

  updateConfig: (id, key, value) =>
    set({
      nodes: get().nodes.map((n) =>
        n.id === id
          ? { ...n, data: { ...n.data, config: { ...n.data.config, [key]: value } } }
          : n,
      ),
    }),

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

  workflowDoc: () => {
    const { nodes, edges } = get();
    return {
      pyflow_version: "1.0",
      id: "current",
      name: "Studio workflow",
      nodes: nodes.map((n) => ({
        id: n.id,
        type: (n.data as PyflowNodeData).toolType,
        position: { x: n.position.x, y: n.position.y },
        config: (n.data as PyflowNodeData).config,
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: { node: e.source, anchor: e.sourceHandle || "out" },
        target: { node: e.target, anchor: e.targetHandle || "in" },
      })),
    };
  },
}));

// Dev/E2E affordance: expose the store for inspection from the console.
if (typeof window !== "undefined") {
  (window as unknown as { pfStore: typeof useStore }).pfStore = useStore;
}
