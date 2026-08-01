import { useEffect, useRef, useState } from "react";
import type { NodeProps } from "@xyflow/react";
import { ANNOTATION_WIDTH } from "../annotations";
import { useStore } from "../store";
import type { AnnotationData } from "../types";

export function AnnotationNode({ id, data, selected }: NodeProps) {
  const d = data as unknown as AnnotationData;
  const updateAnnotation = useStore((s) => s.updateAnnotation);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(d.text);
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (editing) ref.current?.focus();
  }, [editing]);

  const commit = () => {
    setEditing(false);
    if (draft !== d.text) updateAnnotation(id, { text: draft });
  };

  return (
    <div
      className={`pf-annotation ${selected ? "selected" : ""}`}
      style={{
        width: ANNOTATION_WIDTH,
        background: `${d.color}1f`,
        borderColor: `${d.color}99`,
      }}
      onDoubleClick={(e) => {
        e.stopPropagation();
        setDraft(d.text);
        setEditing(true);
      }}
    >
      {editing ? (
        <textarea
          ref={ref}
          className="pf-annotation-input nodrag nopan"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          rows={3}
          placeholder="Comment…"
        />
      ) : d.text ? (
        <div className="pf-annotation-text">{d.text}</div>
      ) : (
        <div className="pf-annotation-empty">Double-click to edit</div>
      )}
    </div>
  );
}
