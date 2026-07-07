import { useEffect, useRef, useState } from "react";
import { inspectConnection, validateFormula } from "../api";
import { useStore } from "../store";
import type { ConfigField, FormulaValidation, PyflowNodeData, SchemaField } from "../types";

const PYFLOW_TYPES = [
  "",
  "string",
  "int64",
  "int32",
  "float64",
  "float32",
  "bool",
  "date",
  "datetime",
];

interface Ctx {
  columns: SchemaField[];
  anchorColumns: Record<string, SchemaField[]>;
}

type OnChange = (v: unknown) => void;

function ColumnSelect({
  columns,
  value,
  onChange,
}: {
  columns: SchemaField[];
  value: unknown;
  onChange: OnChange;
}) {
  const v = (value as string) || "";
  return (
    <select className="pf-input" value={v} onChange={(e) => onChange(e.target.value)}>
      <option value="">— select field —</option>
      {columns.map((c) => (
        <option key={c.name} value={c.name}>
          {c.name}
        </option>
      ))}
      {v && !columns.some((c) => c.name === v) && <option value={v}>{v} (?)</option>}
    </select>
  );
}

function TypeSelect({ value, onChange }: { value: unknown; onChange: OnChange }) {
  return (
    <select className="pf-input" value={(value as string) || ""} onChange={(e) => onChange(e.target.value)}>
      {PYFLOW_TYPES.map((t) => (
        <option key={t} value={t}>
          {t || "(keep)"}
        </option>
      ))}
    </select>
  );
}

function EnumSelect({
  options,
  value,
  onChange,
}: {
  options: string[];
  value: unknown;
  onChange: OnChange;
}) {
  return (
    <select className="pf-input" value={String(value ?? "")} onChange={(e) => onChange(e.target.value)}>
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  );
}

function MultiColumnSelect({
  columns,
  value,
  onChange,
}: {
  columns: SchemaField[];
  value: unknown;
  onChange: OnChange;
}) {
  const arr: string[] = Array.isArray(value) ? (value as string[]) : [];
  const toggle = (name: string) =>
    onChange(arr.includes(name) ? arr.filter((v) => v !== name) : [...arr, name]);
  return (
    <div className="pf-multiselect">
      {columns.length === 0 && <span className="pf-muted">No input fields yet</span>}
      {columns.map((c) => (
        <label key={c.name} className="pf-check">
          <input type="checkbox" checked={arr.includes(c.name)} onChange={() => toggle(c.name)} />
          {c.name}
        </label>
      ))}
    </div>
  );
}

function FormulaInput({
  value,
  columns,
  onChange,
}: {
  value: unknown;
  columns: SchemaField[];
  onChange: OnChange;
}) {
  const [status, setStatus] = useState<FormulaValidation | undefined>();
  const ref = useRef<HTMLTextAreaElement>(null);
  const text = (value as string) || "";

  useEffect(() => {
    if (!text.trim()) {
      setStatus(undefined);
      return;
    }
    const schema = Object.fromEntries(columns.map((c) => [c.name, c.type]));
    const h = setTimeout(() => {
      validateFormula(text, schema).then(setStatus).catch(() => {});
    }, 400);
    return () => clearTimeout(h);
  }, [text, columns]);

  const insert = (snippet: string) => {
    const el = ref.current;
    const pos = el ? el.selectionStart : text.length;
    onChange(text.slice(0, pos) + snippet + text.slice(pos));
  };

  return (
    <div className="pf-formula">
      <textarea
        ref={ref}
        className="pf-input pf-formula-input"
        rows={2}
        value={text}
        onChange={(e) => onChange(e.target.value)}
        placeholder={'IF [spend] > 1000 THEN "VIP" ELSE "Std" ENDIF'}
      />
      {columns.length > 0 && (
        <div className="pf-formula-chips">
          {columns.slice(0, 16).map((c) => (
            <button
              type="button"
              key={c.name}
              className="pf-chip-btn"
              onClick={() => insert(`[${c.name}]`)}
            >
              {c.name}
            </button>
          ))}
        </div>
      )}
      {status &&
        (status.ok ? (
          <div className="pf-ok">✓ returns {status.type}</div>
        ) : (
          <div className="pf-err">{status.error}</div>
        ))}
    </div>
  );
}

function ScalarInput({
  field,
  value,
  ctx,
  onChange,
}: {
  field: ConfigField;
  value: unknown;
  ctx: Ctx;
  onChange: OnChange;
}) {
  const [editorKind, editorAnchor] = (field.editor ?? "").split(":");
  const colsFor = editorAnchor ? ctx.anchorColumns[editorAnchor] ?? [] : ctx.columns;
  if (editorKind === "field") return <ColumnSelect columns={colsFor} value={value} onChange={onChange} />;
  if (editorKind === "type") return <TypeSelect value={value} onChange={onChange} />;
  if (editorKind === "formula") return <FormulaInput value={value} columns={ctx.columns} onChange={onChange} />;
  if (editorKind === "sql")
    return (
      <textarea
        className="pf-input pf-formula-input"
        rows={4}
        value={value === undefined || value === null ? "" : String(value)}
        onChange={(e) => onChange(e.target.value)}
        placeholder="SELECT * FROM my_table WHERE ..."
      />
    );
  if (editorKind === "python")
    return (
      <textarea
        className="pf-input pf-code-input"
        rows={14}
        spellCheck={false}
        value={value === undefined || value === null ? "" : String(value)}
        onChange={(e) => onChange(e.target.value)}
        placeholder="# input1..input3 -> output1..output3"
      />
    );
  if (editorKind === "secret")
    return (
      <input
        className="pf-input"
        type="password"
        autoComplete="off"
        value={value === undefined || value === null ? "" : String(value)}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  if (field.type === "enum") return <EnumSelect options={field.enum ?? []} value={value} onChange={onChange} />;
  if (field.type === "boolean")
    return <input type="checkbox" checked={Boolean(value)} onChange={(e) => onChange(e.target.checked)} />;
  if (field.type === "integer" || field.type === "number")
    return (
      <input
        className="pf-input"
        type="number"
        value={value === undefined || value === null ? "" : String(value)}
        onChange={(e) =>
          onChange(
            field.type === "integer"
              ? parseInt(e.target.value || "0", 10)
              : parseFloat(e.target.value || "0"),
          )
        }
      />
    );
  return (
    <input
      className="pf-input"
      type="text"
      value={value === undefined || value === null ? "" : String(value)}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

function ArrayEditor({
  field,
  value,
  ctx,
  onChange,
}: {
  field: ConfigField;
  value: unknown;
  ctx: Ctx;
  onChange: OnChange;
}) {
  const rows: Record<string, unknown>[] = Array.isArray(value) ? (value as Record<string, unknown>[]) : [];
  const item = field.item ?? [];
  const update = (i: number, key: string, v: unknown) =>
    onChange(rows.map((r, idx) => (idx === i ? { ...r, [key]: v } : r)));
  const addRow = () => onChange([...rows, { ...(field.itemDefaults ?? {}) }]);
  const removeRow = (i: number) => onChange(rows.filter((_, idx) => idx !== i));
  const fieldSub = item.find((s) => s.editor === "field");
  const addAll = () => {
    if (!fieldSub) return addRow();
    onChange(ctx.columns.map((c) => ({ ...(field.itemDefaults ?? {}), [fieldSub.name]: c.name })));
  };

  return (
    <div className="pf-array">
      {rows.map((row, i) => (
        <div className="pf-array-row" key={i}>
          <div className="pf-array-fields">
            {item.map((sf) => (
              <label className="pf-subfield" key={sf.name}>
                <span className="pf-subfield-label">{sf.title}</span>
                <ScalarInput field={sf} value={row[sf.name]} ctx={ctx} onChange={(v) => update(i, sf.name, v)} />
              </label>
            ))}
          </div>
          <button type="button" className="pf-x" title="Remove" onClick={() => removeRow(i)}>
            ×
          </button>
        </div>
      ))}
      <div className="pf-array-actions">
        <button type="button" className="pf-btn-sm" onClick={addRow}>
          + Add
        </button>
        {fieldSub && (
          <button type="button" className="pf-btn-sm" onClick={addAll}>
            + All fields
          </button>
        )}
      </div>
    </div>
  );
}

function FieldControl({
  field,
  value,
  ctx,
  onChange,
}: {
  field: ConfigField;
  value: unknown;
  ctx: Ctx;
  onChange: OnChange;
}) {
  const [editorKind, editorAnchor] = (field.editor ?? "").split(":");
  if (field.type === "array") {
    if (editorKind === "fields") {
      const cols = editorAnchor ? ctx.anchorColumns[editorAnchor] ?? [] : ctx.columns;
      return <MultiColumnSelect columns={cols} value={value} onChange={onChange} />;
    }
    if (field.item) return <ArrayEditor field={field} value={value} ctx={ctx} onChange={onChange} />;
    return <MultiColumnSelect columns={ctx.columns} value={value} onChange={onChange} />;
  }
  return <ScalarInput field={field} value={value} ctx={ctx} onChange={onChange} />;
}

function DbActions({ nodeId, config }: { nodeId: string; config: Record<string, unknown> }) {
  const updateConfig = useStore((s) => s.updateConfig);
  const [status, setStatus] = useState<{ busy?: boolean; ok?: boolean; msg?: string }>({});

  const fetchSchema = async () => {
    setStatus({ busy: true });
    try {
      const res = await inspectConnection(config);
      if (res.ok && res.columns) {
        updateConfig(nodeId, "columns", res.columns);
        setStatus({ ok: true, msg: `Connected — ${res.columns.length} columns` });
      } else {
        setStatus({ ok: false, msg: res.error || "Connection failed" });
      }
    } catch (e) {
      setStatus({ ok: false, msg: String(e) });
    }
  };

  return (
    <div className="pf-db-actions">
      <button type="button" className="pf-btn-sm" onClick={fetchSchema} disabled={status.busy}>
        {status.busy ? "Connecting…" : "Test connection & fetch schema"}
      </button>
      {status.msg && <div className={status.ok ? "pf-ok" : "pf-err"}>{status.msg}</div>}
    </div>
  );
}

export function ConfigPanel() {
  const selectedId = useStore((s) => s.selectedId);
  const nodes = useStore((s) => s.nodes);
  const catalog = useStore((s) => s.catalog);
  const schemas = useStore((s) => s.schemas);
  const updateConfig = useStore((s) => s.updateConfig);

  const node = nodes.find((n) => n.id === selectedId);
  if (!node) {
    return (
      <aside className="pf-config">
        <div className="pf-panel-title">Configuration</div>
        <p className="pf-empty">Select a tool on the canvas to configure it.</p>
      </aside>
    );
  }

  const data = node.data as PyflowNodeData;
  const tool = catalog.find((t) => t.type === data.toolType);
  const nodeSchema = selectedId ? schemas[selectedId] : undefined;

  const anchorColumns: Record<string, SchemaField[]> = {};
  for (const [anchor, sch] of Object.entries(nodeSchema?.inputs ?? {})) {
    if (sch) anchorColumns[anchor] = sch.fields;
  }
  const inputCols: SchemaField[] = (() => {
    for (const anchor of Object.values(nodeSchema?.inputs ?? {})) if (anchor) return anchor.fields;
    return [];
  })();
  const ctx: Ctx = { columns: inputCols, anchorColumns };
  const outputs = nodeSchema?.outputs ?? {};

  return (
    <aside className="pf-config">
      <div className="pf-panel-title">{data.name}</div>
      <div className="pf-panel-subtitle pf-muted">{data.toolType}</div>
      {nodeSchema?.error && <div className="pf-err pf-config-err">{nodeSchema.error}</div>}

      <div className="pf-fields">
        {(() => {
          const visible = (tool?.configFields ?? []).filter((f) => f.editor !== "hidden");
          if (visible.length === 0) return <p className="pf-empty">This tool has no options.</p>;
          return visible.map((f) => (
            <div className="pf-field" key={f.name}>
              <span className="pf-field-label">{f.title}</span>
              <FieldControl
                field={f}
                value={data.config[f.name]}
                ctx={ctx}
                onChange={(v) => updateConfig(node.id, f.name, v)}
              />
              {f.help && <small className="pf-muted">{f.help}</small>}
            </div>
          ));
        })()}
        {(tool?.configFields ?? []).some((f) => f.editor === "sql") && (
          <DbActions nodeId={node.id} config={data.config} />
        )}
      </div>

      <div className="pf-outputs">
        <div className="pf-panel-subtitle">Output fields</div>
        {Object.keys(outputs).length === 0 && (
          <span className="pf-muted">Configure the tool to see its output fields.</span>
        )}
        {Object.entries(outputs).map(([anchor, sch]) => (
          <div key={anchor} className="pf-output-anchor">
            {Object.keys(outputs).length > 1 && <div className="pf-anchor-tag">{anchor}</div>}
            <div className="pf-field-chips">
              {sch ? (
                sch.fields.map((fld) => (
                  <span key={fld.name} className="pf-fieldchip" title={fld.type}>
                    {fld.name}
                    <i>{fld.type}</i>
                  </span>
                ))
              ) : (
                <span className="pf-muted">—</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
