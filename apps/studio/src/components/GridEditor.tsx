// Editable data grid for the Text Input tool. The value is a table object
// { columns: [{name, type}], rows: string[][] }; onChange writes a new one.
import { useState } from "react";

const GRID_TYPES = ["string", "int64", "float64", "bool", "date", "datetime"];

interface GridCol {
  name: string;
  type: string;
}
interface GridTable {
  columns: GridCol[];
  rows: string[][];
}

function normalize(value: unknown): GridTable {
  const v = (value ?? {}) as { columns?: unknown; rows?: unknown };
  const columns: GridCol[] = Array.isArray(v.columns)
    ? v.columns.map((c) => {
        const o = (c ?? {}) as { name?: unknown; type?: unknown };
        return { name: String(o.name ?? ""), type: String(o.type ?? "string") };
      })
    : [];
  const rows: string[][] = Array.isArray(v.rows)
    ? v.rows.map((r) => (Array.isArray(r) ? r.map((cell) => (cell == null ? "" : String(cell))) : []))
    : [];
  return { columns, rows };
}

// --- clipboard paste --------------------------------------------------------

// Split pasted text into a 2-D array. Prefer tabs (Excel / Google Sheets copies
// are tab-separated); fall back to commas.
function splitGrid(text: string): string[][] {
  const lines = text.replace(/\r\n?/g, "\n").split("\n");
  while (lines.length && lines[lines.length - 1] === "") lines.pop();
  const delim = text.includes("\t") ? "\t" : ",";
  return lines.map((l) => l.split(delim));
}

// Guess a column's type from its values. Conservative: leading-zero numbers stay
// strings (ZIP codes, ids), and 0/1 read as ints rather than booleans.
function inferType(cells: string[]): string {
  const vals = cells.map((c) => c.trim()).filter((c) => c !== "");
  if (!vals.length) return "string";
  // A leading zero before another digit (01234, 00789, 01.5) means the zero is
  // significant — keep the whole column as text so casting doesn't drop it.
  if (vals.some((v) => /^-?0\d/.test(v))) return "string";
  const int = /^-?\d+$/;
  const float = /^-?(\d+\.\d*|\.\d+|\d+)([eE][+-]?\d+)?$/;
  const bool = /^(true|false|yes|no|t|f|y|n)$/i;
  const date = /^\d{4}-\d{2}-\d{2}$/;
  if (vals.every((v) => int.test(v))) return "int64";
  if (vals.every((v) => float.test(v))) return "float64";
  if (vals.every((v) => bool.test(v))) return "bool";
  if (vals.every((v) => date.test(v))) return "date";
  return "string";
}

function tableFromPaste(text: string, firstRowHeader: boolean): GridTable {
  const grid = splitGrid(text);
  if (!grid.length) return { columns: [], rows: [] };
  const width = Math.max(...grid.map((r) => r.length));
  const rows2d = grid.map((r) => {
    const nr = [...r];
    while (nr.length < width) nr.push("");
    return nr;
  });

  let names: string[];
  let dataRows: string[][];
  if (firstRowHeader) {
    names = rows2d[0].map((h, i) => h.trim() || `Column${i + 1}`);
    dataRows = rows2d.slice(1);
  } else {
    names = Array.from({ length: width }, (_, i) => `Column${i + 1}`);
    dataRows = rows2d;
  }

  // De-duplicate header names so Polars doesn't choke on collisions.
  const seen = new Map<string, number>();
  names = names.map((h) => {
    const n = seen.get(h) ?? 0;
    seen.set(h, n + 1);
    return n ? `${h}_${n}` : h;
  });

  const columns = names.map((name, i) => ({ name, type: inferType(dataRows.map((r) => r[i] ?? "")) }));
  return { columns, rows: dataRows };
}

export function GridEditor({
  value,
  onChange,
}: {
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const table = normalize(value);
  const { columns, rows } = table;
  const width = columns.length;

  const [pasting, setPasting] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [firstRowHeader, setFirstRowHeader] = useState(true);

  const emit = (next: GridTable) => onChange(next);

  const setColName = (i: number, name: string) =>
    emit({ ...table, columns: columns.map((c, idx) => (idx === i ? { ...c, name } : c)) });
  const setColType = (i: number, type: string) =>
    emit({ ...table, columns: columns.map((c, idx) => (idx === i ? { ...c, type } : c)) });
  const addColumn = () =>
    emit({
      columns: [...columns, { name: `Column${columns.length + 1}`, type: "string" }],
      rows: rows.map((r) => [...r, ""]),
    });
  const removeColumn = (i: number) =>
    emit({
      columns: columns.filter((_, idx) => idx !== i),
      rows: rows.map((r) => r.filter((_, idx) => idx !== i)),
    });
  const addRow = () => emit({ ...table, rows: [...rows, Array(Math.max(width, 1)).fill("")] });
  const removeRow = (j: number) => emit({ ...table, rows: rows.filter((_, idx) => idx !== j) });
  const setCell = (j: number, i: number, val: string) =>
    emit({
      ...table,
      rows: rows.map((r, rIdx) => {
        if (rIdx !== j) return r;
        const nr = [...r];
        while (nr.length < width) nr.push("");
        nr[i] = val;
        return nr;
      }),
    });

  const openPaste = async () => {
    setPasteText("");
    setPasting(true);
    // Best-effort one-click: prefill from the clipboard if the browser allows it;
    // otherwise the user just pastes into the textarea with Ctrl+V.
    try {
      const t = await navigator.clipboard.readText();
      if (t) setPasteText(t);
    } catch {
      /* clipboard read blocked — manual paste */
    }
  };
  const applyPaste = () => {
    const next = tableFromPaste(pasteText, firstRowHeader);
    if (next.columns.length) emit(next);
    setPasting(false);
    setPasteText("");
  };
  const cancelPaste = () => {
    setPasting(false);
    setPasteText("");
  };

  return (
    <div className="pf-grid">
      {columns.length === 0 && !pasting && (
        <div className="pf-muted">Add a column or paste data to start.</div>
      )}
      <div className="pf-grid-scroll">
        <table className="pf-grid-table">
          <thead>
            <tr>
              {columns.map((c, i) => (
                <th key={i}>
                  <input
                    className="pf-grid-name"
                    value={c.name}
                    placeholder="name"
                    onChange={(e) => setColName(i, e.target.value)}
                  />
                  <div className="pf-grid-colctrl">
                    <select
                      className="pf-grid-type"
                      value={c.type}
                      onChange={(e) => setColType(i, e.target.value)}
                    >
                      {GRID_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                    <button type="button" className="pf-x" title="Remove column" onClick={() => removeColumn(i)}>
                      ×
                    </button>
                  </div>
                </th>
              ))}
              <th className="pf-grid-addcol">
                <button type="button" className="pf-btn-sm" onClick={addColumn}>
                  + Col
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, j) => (
              <tr key={j}>
                {columns.map((_, i) => (
                  <td key={i}>
                    <input
                      className="pf-grid-cell"
                      value={r[i] ?? ""}
                      onChange={(e) => setCell(j, i, e.target.value)}
                    />
                  </td>
                ))}
                <td className="pf-grid-rowctrl">
                  <button type="button" className="pf-x" title="Remove row" onClick={() => removeRow(j)}>
                    ×
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="pf-grid-actions">
        <button type="button" className="pf-btn-sm" onClick={addRow} disabled={width === 0}>
          + Row
        </button>
        <button type="button" className="pf-btn-sm" onClick={openPaste}>
          Paste
        </button>
        <span className="pf-muted">
          {rows.length} rows · {columns.length} cols
        </span>
      </div>

      {pasting && (
        <div className="pf-grid-paste">
          <textarea
            className="pf-input pf-grid-paste-area"
            rows={5}
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
            placeholder="Paste tab- or comma-separated rows (e.g. copied from Excel), then Load."
            autoFocus
          />
          <label className="pf-check">
            <input
              type="checkbox"
              checked={firstRowHeader}
              onChange={(e) => setFirstRowHeader(e.target.checked)}
            />
            First row is a header
          </label>
          <div className="pf-grid-paste-actions">
            <button type="button" className="pf-btn-sm" onClick={applyPaste} disabled={!pasteText.trim()}>
              Load into grid
            </button>
            <button type="button" className="pf-btn-sm" onClick={cancelPaste}>
              Cancel
            </button>
          </div>
          <small className="pf-muted">Replaces the grid; column types are guessed — adjust after.</small>
        </div>
      )}
    </div>
  );
}
