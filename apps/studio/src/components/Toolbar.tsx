import { useState } from "react";

import {
  fetchPreview,
  fetchSchemas,
  listWorkflowFiles,
  readWorkflowFile,
  runWorkflow,
  saveWorkflowFile,
  type WorkflowFile,
} from "../api";
import { useStore } from "../store";
import type { PyflowNodeData } from "../types";

export function Toolbar() {
  const running = useStore((s) => s.running);
  const loadExample = useStore((s) => s.loadExample);
  const clearCanvas = useStore((s) => s.clearCanvas);
  const currentName = useStore((s) => s.currentName);
  const undo = useStore((s) => s.undo);
  const redo = useStore((s) => s.redo);
  const canUndo = useStore((s) => s.past.length > 0);
  const canRedo = useStore((s) => s.future.length > 0);
  const [openMenu, setOpenMenu] = useState(false);
  const [files, setFiles] = useState<WorkflowFile[]>([]);

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
      try {
        const schemas = await fetchSchemas(st.workflowDoc());
        st.setSchemas(schemas);
      } catch {
        /* keep existing schemas */
      }
    }
  };

  const save = async () => {
    const st = useStore.getState();
    const input = window.prompt("Save workflow as:", st.currentName ?? "");
    if (input === null) return;
    const name = input.trim().replace(/[^A-Za-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "");
    if (!name) {
      st.addMessage({ level: "error", text: "Enter a name (letters, numbers, - or _)." });
      return;
    }
    try {
      const res = await saveWorkflowFile(name, st.workflowDoc());
      st.setCurrentName(res.name);
      st.addMessage({ level: "info", text: `Saved workflow "${res.name}"` });
    } catch (e) {
      st.addMessage({ level: "error", text: `Save failed: ${e}` });
    }
  };

  const toggleOpen = async () => {
    if (openMenu) {
      setOpenMenu(false);
      return;
    }
    try {
      setFiles(await listWorkflowFiles());
      setOpenMenu(true);
    } catch (e) {
      useStore.getState().addMessage({ level: "error", text: `Could not list workflows: ${e}` });
    }
  };

  const openFile = async (name: string) => {
    setOpenMenu(false);
    const st = useStore.getState();
    try {
      const doc = await readWorkflowFile(name);
      st.loadDoc(doc);
      st.setCurrentName(name);
      st.addMessage({ level: "info", text: `Opened "${name}"` });
    } catch (e) {
      st.addMessage({ level: "error", text: `Open failed: ${e}` });
    }
  };

  return (
    <div className="pf-toolbar">
      <span className="pf-brand">
        <span className="pf-logo">▷</span> Pyflow <b>Studio</b>
      </span>
      {currentName && <span className="pf-filename">{currentName}.pyflow</span>}
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
      <button className="pf-btn" onClick={undo} disabled={running || !canUndo} title="Undo (Ctrl+Z)">
        ↶
      </button>
      <button className="pf-btn" onClick={redo} disabled={running || !canRedo} title="Redo (Ctrl+Shift+Z)">
        ↷
      </button>
      <div className="pf-open-wrap">
        <button className="pf-btn" onClick={toggleOpen} disabled={running}>
          Open ▾
        </button>
        {openMenu && (
          <>
            <div className="pf-menu-backdrop" onClick={() => setOpenMenu(false)} />
            <div className="pf-menu">
              {files.length === 0 ? (
                <div className="pf-menu-empty">No saved workflows yet</div>
              ) : (
                files.map((f) => (
                  <button key={f.name} className="pf-menu-item" onClick={() => openFile(f.name)}>
                    {f.name}
                  </button>
                ))
              )}
            </div>
          </>
        )}
      </div>
      <button className="pf-btn" onClick={save} disabled={running}>
        Save
      </button>
      <button className="pf-btn" onClick={loadExample} disabled={running}>
        Load example
      </button>
      <button className="pf-btn" onClick={clearCanvas} disabled={running}>
        Clear
      </button>
      <span className="pf-hint">
        Run · Save/Open · Undo Ctrl+Z · Copy/Paste Ctrl+C/V · Shift-drag to multi-select
      </span>
    </div>
  );
}
