import { fetchPreview, fetchSchemas, runWorkflow } from "../api";
import { useStore } from "../store";
import type { PyflowNodeData } from "../types";

export function Toolbar() {
  const running = useStore((s) => s.running);
  const loadExample = useStore((s) => s.loadExample);
  const clearCanvas = useStore((s) => s.clearCanvas);

  const run = async (clearCache = false) => {
    const s = useStore.getState();
    s.resetRun();
    s.setRunning(true);
    const doc = s.workflowDoc();

    try {
      await runWorkflow(
        doc,
        (e) => {
          const st = useStore.getState();
          if (e.type === "node_started") {
            st.patchNode(e.node, { status: "running" });
          } else if (e.type === "node_completed") {
            st.patchNode(e.node, {
              status: "done",
              rows: e.rows,
              anchorRows: e.anchor_rows,
              cached: e.cached,
            });
          } else if (e.type === "node_error") {
            st.patchNode(e.node, { status: "error" });
            st.addMessage({ level: "error", text: e.detail, node: e.node });
          } else if (e.type === "node_message") {
            st.addMessage({ level: e.level, text: e.text, node: e.node });
          } else if (e.type === "run_error") {
            st.addMessage({ level: "error", text: `${e.code}: ${e.detail}` });
          } else if (e.type === "run_completed" && e.computed !== undefined) {
            st.addMessage({
              level: "info",
              text: `Run complete — computed ${e.computed}, reused ${e.cached} cached`,
            });
          }
        },
        clearCache,
      );
    } catch (err) {
      useStore.getState().addMessage({ level: "error", text: String(err) });
    } finally {
      const st = useStore.getState();
      st.setRunning(false);
      // Refresh the preview for the currently selected node.
      const sel = st.selectedId;
      if (sel) {
        const node = st.nodes.find((n) => n.id === sel);
        const anchor = (node?.data as PyflowNodeData | undefined)?.outputs[0]?.id;
        try {
          const pv = await fetchPreview(sel, anchor);
          st.setPreview(pv, anchor);
        } catch {
          /* no preview */
        }
      }
      // Refresh schemas so data-dependent columns (Cross Tab / Transpose) that only
      // become known after a run propagate to downstream field pickers.
      try {
        const schemas = await fetchSchemas(st.workflowDoc());
        st.setSchemas(schemas);
      } catch {
        /* keep existing schemas */
      }
    }
  };

  return (
    <div className="pf-toolbar">
      <span className="pf-brand">
        <span className="pf-logo">▷</span> Pyflow <b>Studio</b>
      </span>
      <button className="pf-run" onClick={() => run(false)} disabled={running}>
        {running ? "Running…" : "▶ Run"}
      </button>
      <button
        className="pf-btn"
        onClick={() => run(true)}
        disabled={running}
        title="Clear the cache and recompute every node"
      >
        ↻ Fresh
      </button>
      <button className="pf-btn" onClick={loadExample} disabled={running}>
        Load example
      </button>
      <button className="pf-btn" onClick={clearCanvas} disabled={running}>
        Clear
      </button>
      <span className="pf-hint">Drag tools from the left · connect anchors · Run</span>
    </div>
  );
}
