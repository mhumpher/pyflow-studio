import { useCallback, useEffect, useMemo } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { fetchFunctions, fetchSchemas, fetchTools } from "./api";
import { useStore } from "./store";
import type { PyflowNodeData } from "./types";
import { PyflowNode } from "./components/PyflowNode";
import { Palette } from "./components/Palette";
import { ConfigPanel } from "./components/ConfigPanel";
import { ResultsPanel } from "./components/ResultsPanel";
import { Toolbar } from "./components/Toolbar";

const nodeTypes = { pyflow: PyflowNode };

function Canvas() {
  const nodes = useStore((s) => s.nodes);
  const edges = useStore((s) => s.edges);
  const onNodesChange = useStore((s) => s.onNodesChange);
  const onEdgesChange = useStore((s) => s.onEdgesChange);
  const onConnect = useStore((s) => s.onConnect);
  const addNode = useStore((s) => s.addNode);
  const select = useStore((s) => s.select);
  const catalog = useStore((s) => s.catalog);
  const fitSignal = useStore((s) => s.fitSignal);
  const rf = useReactFlow();

  useEffect(() => {
    if (fitSignal > 0) rf.fitView({ padding: 0.25, duration: 300 });
  }, [fitSignal, rf]);

  const onDrop = useCallback(
    (ev: React.DragEvent) => {
      ev.preventDefault();
      const type = ev.dataTransfer.getData("application/pyflow-tool");
      const tool = catalog.find((t) => t.type === type);
      if (!tool) return;
      const pos = rf.screenToFlowPosition({ x: ev.clientX, y: ev.clientY });
      addNode(tool, pos);
    },
    [catalog, rf, addNode],
  );

  const onDragOver = useCallback((ev: React.DragEvent) => {
    ev.preventDefault();
    ev.dataTransfer.dropEffect = "move";
  }, []);

  return (
    <div className="pf-canvas" onDrop={onDrop} onDragOver={onDragOver}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={(_, n) => select(n.id)}
        onPaneClick={() => select(undefined)}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={16} color="#2a3346" />
        <Controls />
        <MiniMap
          pannable
          zoomable
          style={{ background: "#161c2b" }}
          maskColor="rgba(15, 20, 32, 0.6)"
          nodeColor="#3b82f6"
        />
      </ReactFlow>
    </div>
  );
}

export default function App() {
  const setCatalog = useStore((s) => s.setCatalog);
  const setFunctions = useStore((s) => s.setFunctions);
  const setSchemas = useStore((s) => s.setSchemas);
  const nodes = useStore((s) => s.nodes);
  const edges = useStore((s) => s.edges);

  useEffect(() => {
    fetchTools()
      .then(setCatalog)
      .catch((err) => console.error("Failed to load tools:", err));
    fetchFunctions()
      .then(setFunctions)
      .catch(() => {});
  }, [setCatalog, setFunctions]);

  // Recompute design-time schemas when the graph structure or any config changes
  // (ignoring node position moves), debounced.
  const structureSig = useMemo(
    () =>
      JSON.stringify({
        n: nodes.map((n) => ({
          id: n.id,
          t: (n.data as PyflowNodeData).toolType,
          c: (n.data as PyflowNodeData).config,
        })),
        e: edges.map((e) => ({ s: e.source, sh: e.sourceHandle, t: e.target, th: e.targetHandle })),
      }),
    [nodes, edges],
  );

  useEffect(() => {
    const doc = useStore.getState().workflowDoc();
    const handle = setTimeout(() => {
      fetchSchemas(doc)
        .then(setSchemas)
        .catch(() => {});
    }, 350);
    return () => clearTimeout(handle);
  }, [structureSig, setSchemas]);

  return (
    <ReactFlowProvider>
      <div className="pf-app">
        <Toolbar />
        <div className="pf-main">
          <Palette />
          <Canvas />
          <ConfigPanel />
        </div>
        <ResultsPanel />
      </div>
    </ReactFlowProvider>
  );
}
