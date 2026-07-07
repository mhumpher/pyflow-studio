import { useEffect, useState } from "react";
import { fetchPreview } from "../api";
import { useStore } from "../store";
import type { PreviewData, PyflowNodeData } from "../types";

type Tab = "data" | "meta" | "msgs";

function DataGrid({ preview }: { preview: PreviewData }) {
  const { columns, rows } = preview.grid;
  return (
    <div className="pf-grid-wrap">
      <table className="pf-grid">
        <thead>
          <tr>
            <th className="pf-rownum">#</th>
            {columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td className="pf-rownum">{i + 1}</td>
              {r.map((v, j) => (
                <td key={j}>
                  {v === null ? <span className="pf-null">null</span> : String(v)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ResultsPanel() {
  const selectedId = useStore((s) => s.selectedId);
  const nodes = useStore((s) => s.nodes);
  const preview = useStore((s) => s.preview);
  const previewAnchor = useStore((s) => s.previewAnchor);
  const setPreview = useStore((s) => s.setPreview);
  const messages = useStore((s) => s.messages);
  const [tab, setTab] = useState<Tab>("data");

  const node = nodes.find((n) => n.id === selectedId);
  const data = node?.data as PyflowNodeData | undefined;
  const outputs = data?.outputs ?? [];

  useEffect(() => {
    if (!selectedId) {
      setPreview(undefined);
      return;
    }
    const anchor = outputs[0]?.id;
    fetchPreview(selectedId, anchor)
      .then((pv) => setPreview(pv, anchor))
      .catch(() => setPreview(undefined));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  const loadAnchor = (a: string) => {
    if (!selectedId) return;
    fetchPreview(selectedId, a)
      .then((pv) => setPreview(pv, a))
      .catch(() => {});
  };

  return (
    <div className="pf-results">
      <div className="pf-results-head">
        <div className="pf-tabs">
          <button className={tab === "data" ? "active" : ""} onClick={() => setTab("data")}>
            Data
          </button>
          <button className={tab === "meta" ? "active" : ""} onClick={() => setTab("meta")}>
            Metadata
          </button>
          <button className={tab === "msgs" ? "active" : ""} onClick={() => setTab("msgs")}>
            Messages{messages.length ? ` (${messages.length})` : ""}
          </button>
        </div>
        {outputs.length > 1 && (
          <div className="pf-anchor-pick">
            {outputs.map((o) => (
              <button
                key={o.id}
                className={previewAnchor === o.id ? "active" : ""}
                onClick={() => loadAnchor(o.id)}
              >
                {o.label || o.id}
              </button>
            ))}
          </div>
        )}
        {preview && <span className="pf-count">{preview.count.toLocaleString()} rows</span>}
      </div>

      <div className="pf-results-body">
        {tab === "data" &&
          (preview ? (
            <DataGrid preview={preview} />
          ) : (
            <p className="pf-empty">Run the workflow, then select a tool to preview its output.</p>
          ))}
        {tab === "meta" &&
          (preview ? (
            <table className="pf-grid">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Type</th>
                </tr>
              </thead>
              <tbody>
                {preview.schema.fields.map((f) => (
                  <tr key={f.name}>
                    <td>{f.name}</td>
                    <td className="pf-muted">{f.type}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="pf-empty">No metadata yet.</p>
          ))}
        {tab === "msgs" &&
          (messages.length ? (
            <ul className="pf-msgs">
              {messages.map((m, i) => (
                <li key={i} className={`lvl-${m.level}`}>
                  {m.node ? `[${m.node}] ` : ""}
                  {m.text}
                </li>
              ))}
            </ul>
          ) : (
            <p className="pf-empty">No messages.</p>
          ))}
      </div>
    </div>
  );
}
