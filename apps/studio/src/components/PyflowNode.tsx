import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { PyflowNodeData } from "../types";

const HEADER = 38;
const GAP = 20;

export function PyflowNode({ data, selected }: NodeProps) {
  const d = data as unknown as PyflowNodeData;
  const height = HEADER + Math.max(d.inputs.length, d.outputs.length, 1) * GAP;

  return (
    <div
      className={`pf-node status-${d.status} ${selected ? "selected" : ""}`}
      style={{ minHeight: height }}
    >
      <div className="pf-node-header">
        <span className="pf-dot" />
        <span className="pf-node-name">{d.name}</span>
      </div>
      {typeof d.rows === "number" && (
        <div className="pf-node-rows">
          {d.rows.toLocaleString()} rows
          {d.cached && <span className="pf-cached">❄ cached</span>}
        </div>
      )}

      {d.inputs.map((a, i) => (
        <div key={a.id}>
          <Handle id={a.id} type="target" position={Position.Left} style={{ top: HEADER + i * GAP }} />
          {d.inputs.length > 1 && (
            <span
              className="pf-anchor-label pf-anchor-label-left"
              style={{ top: HEADER + i * GAP - 9 }}
            >
              {a.label || a.id}
            </span>
          )}
        </div>
      ))}

      {d.outputs.map((a, i) => (
        <div key={a.id}>
          <Handle
            id={a.id}
            type="source"
            position={Position.Right}
            style={{ top: HEADER + i * GAP }}
          />
          {d.outputs.length > 1 && (
            <span className="pf-anchor-label" style={{ top: HEADER + i * GAP - 9 }}>
              {a.label || a.id}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
