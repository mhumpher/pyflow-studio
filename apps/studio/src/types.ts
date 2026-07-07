export interface AnchorDesc {
  id: string;
  label?: string;
  contract?: string;
  multi?: boolean;
}

export type ConfigFieldType =
  | "string"
  | "integer"
  | "number"
  | "boolean"
  | "enum"
  | "array";

export interface ConfigField {
  name: string;
  title: string;
  type: ConfigFieldType;
  enum?: string[];
  default?: unknown;
  help?: string | null;
  editor?: string | null; // "field" | "fields" | "type" | "formula" | "file"
  item?: ConfigField[]; // sub-fields for an array of objects
  itemDefaults?: Record<string, unknown>;
  itemType?: string; // element type for an array of scalars
}

export interface ToolDesc {
  type: string;
  name: string;
  category: string;
  icon: string;
  inputs: AnchorDesc[];
  outputs: AnchorDesc[];
  configFields: ConfigField[];
}

export type NodeStatus = "idle" | "queued" | "running" | "done" | "error";

export interface PyflowNodeData {
  toolType: string;
  name: string;
  inputs: AnchorDesc[];
  outputs: AnchorDesc[];
  config: Record<string, unknown>;
  status: NodeStatus;
  rows?: number;
  anchorRows?: Record<string, number>;
  cached?: boolean;
}

export interface SchemaField {
  name: string;
  type: string;
  nullable?: boolean;
}

export interface PreviewData {
  schema: { fields: SchemaField[] };
  count: number;
  grid: { columns: string[]; rows: unknown[][] };
}

export interface RunMessage {
  level: string;
  text: string;
  node?: string;
}

export interface AnchorSchema {
  fields: SchemaField[];
}

export interface NodeSchemas {
  inputs: Record<string, AnchorSchema | null>;
  outputs: Record<string, AnchorSchema | null>;
  error: string | null;
}

export type SchemaMap = Record<string, NodeSchemas>;

export interface FormulaValidation {
  ok: boolean;
  type?: string;
  error?: string;
}
