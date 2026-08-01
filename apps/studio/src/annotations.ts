// Comment-note colors (shared by the store, the node, and the config panel).
// Kept in a plain module so nothing imports a React component into the store.
export const ANNOTATION_COLORS = [
  "#d9b45b", // amber
  "#5b8bd9", // blue
  "#5bbf8b", // green
  "#d97a5b", // terracotta
  "#8b7bd9", // violet
  "#8a94a6", // slate
];

export const DEFAULT_ANNOTATION_COLOR = ANNOTATION_COLORS[0];
export const ANNOTATION_WIDTH = 220;
