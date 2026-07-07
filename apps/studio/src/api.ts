import type { FormulaValidation, PreviewData, SchemaMap, ToolDesc } from "./types";

// When served by the Python server (production), use same-origin. In Vite dev
// (port 5173) talk to the server on 8710.
const isDev = window.location.port === "5173";
export const API_BASE = isDev ? "http://127.0.0.1:8710" : "";
export const WS_BASE = isDev ? "ws://127.0.0.1:8710" : `ws://${window.location.host}`;

export const WORKFLOW_ID = "current";

export async function fetchTools(): Promise<ToolDesc[]> {
  const res = await fetch(`${API_BASE}/tools`);
  if (!res.ok) throw new Error(`GET /tools failed: ${res.status}`);
  return res.json();
}

export async function fetchPreview(
  nodeId: string,
  anchor?: string,
): Promise<PreviewData> {
  const q = anchor ? `?anchor=${encodeURIComponent(anchor)}` : "";
  const res = await fetch(
    `${API_BASE}/workflows/${WORKFLOW_ID}/nodes/${nodeId}/preview${q}`,
  );
  if (!res.ok) throw new Error(`no preview (${res.status})`);
  return res.json();
}

export async function fetchSchemas(doc: unknown): Promise<SchemaMap> {
  const res = await fetch(`${API_BASE}/workflows/schema`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ workflow: doc, wf_id: WORKFLOW_ID }),
  });
  if (!res.ok) throw new Error(`schema failed (${res.status})`);
  return res.json();
}

export async function fetchFunctions(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/formula/functions`);
  if (!res.ok) throw new Error(`GET /formula/functions failed: ${res.status}`);
  return res.json();
}

export interface InspectResult {
  ok: boolean;
  columns?: { name: string; type: string }[];
  error?: string;
}

export async function inspectConnection(config: unknown): Promise<InspectResult> {
  const res = await fetch(`${API_BASE}/connections/inspect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config }),
  });
  if (!res.ok) throw new Error(`inspect failed (${res.status})`);
  return res.json();
}

export async function validateFormula(
  expression: string,
  schema: Record<string, string>,
): Promise<FormulaValidation> {
  const res = await fetch(`${API_BASE}/formula/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ expression, schema }),
  });
  if (!res.ok) throw new Error(`formula validate failed (${res.status})`);
  return res.json();
}

export function runWorkflow(
  doc: unknown,
  onEvent: (event: any) => void,
  clearCache = false,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(`${WS_BASE}/workflows/${WORKFLOW_ID}/session`);
    ws.onopen = () =>
      ws.send(JSON.stringify({ op: "run", workflow: doc, clear_cache: clearCache }));
    ws.onmessage = (msg) => {
      const event = JSON.parse(msg.data);
      onEvent(event);
      if (["run_completed", "run_error", "run_cancelled"].includes(event.type)) {
        ws.close();
        resolve();
      }
    };
    ws.onerror = () => reject(new Error("WebSocket error (is the server running?)"));
  });
}
