// Editable data grid for the Text Input tool. The value is a table object
// { columns: [{name, type}], rows: string[][] }; onChange writes a new one.

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

  return (
    <div className="pf-grid">
      {columns.length === 0 && <div className="pf-muted">Add a column to start entering data.</div>}
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
        <span className="pf-muted">
          {rows.length} rows · {columns.length} cols
        </span>
      </div>
    </div>
  );
}
