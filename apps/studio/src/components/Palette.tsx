import { useStore } from "../store";
import type { ToolDesc } from "../types";

export function Palette() {
  const catalog = useStore((s) => s.catalog);

  const byCategory: Record<string, ToolDesc[]> = {};
  for (const t of catalog) {
    (byCategory[t.category] ||= []).push(t);
  }

  return (
    <aside className="pf-palette">
      <div className="pf-panel-title">Tools</div>
      {catalog.length === 0 && (
        <p className="pf-empty">No tools loaded. Is the server running?</p>
      )}
      {Object.entries(byCategory).map(([category, tools]) => (
        <div key={category} className="pf-cat">
          <div className="pf-cat-name">{category}</div>
          {tools.map((t) => (
            <div
              key={t.type}
              className="pf-tool"
              draggable
              onDragStart={(e) => {
                e.dataTransfer.setData("application/pyflow-tool", t.type);
                e.dataTransfer.effectAllowed = "move";
              }}
              title={t.type}
            >
              <span className="pf-tool-icon">◆</span>
              {t.name}
            </div>
          ))}
        </div>
      ))}
    </aside>
  );
}
