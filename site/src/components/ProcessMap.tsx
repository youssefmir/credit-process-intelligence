import dagre from "@dagrejs/dagre";
import {
  Background,
  BaseEdge,
  Controls,
  EdgeLabelRenderer,
  getBezierPath,
  Handle,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/base.css";
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { MapEdge, MapNode, ProcessMap as PM } from "../lib/data";
import { num } from "../lib/format";
import { usePalette, type Palette } from "../lib/theme";

type Mode = "frequency" | "performance";
type ViewKey = "milestones" | "complete";

interface StationData extends Record<string, unknown> {
  node: MapNode;
  dim: boolean;
  vertical: boolean;
}

interface FlowData extends Record<string, unknown> {
  edge: MapEdge;
  mode: Mode;
  color: string;
  width: number;
  label: string;
  showLabel: boolean;
  dim: boolean;
}

const NODE_W = 150;
const NODE_H = 42;
const CATEGORY: Record<string, string> = { A: "Demande", O: "Offre", W: "Tâche humaine", S: "" };

function durationLabel(h: number | undefined): string {
  if (h === undefined) return "";
  if (h < 1) return `${num(h * 60)} min`;
  if (h < 48) return `${num(h, h < 10 ? 1 : 0)} h`;
  return `${num(h / 24, 1)} j`;
}

const StationNode = memo(function StationNode({ data }: NodeProps<Node<StationData>>) {
  const n = data.node;
  const terminal = n.category === "S";
  return (
    <div className={`pm-node ${data.dim ? "dim" : ""} ${terminal ? "terminal" : ""} cat-${n.category}`} title={`${n.label} (${CATEGORY[n.category] || "repère"})`}>
      <Handle type="target" position={data.vertical ? Position.Top : Position.Left} className="pm-handle" />
      <span className={`pm-station ${terminal ? "sq" : ""}`} aria-hidden="true" />
      <span className="pm-text">
        <span className="pm-label">{n.short ?? n.label}</span>
        <span className="pm-count">{num(n.count)}</span>
      </span>
      <Handle type="source" position={data.vertical ? Position.Bottom : Position.Right} className="pm-handle" />
    </div>
  );
});

const FlowEdge = memo(function FlowEdge(props: EdgeProps<Edge<FlowData>>) {
  const { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data } = props;
  const [path, lx, ly] = getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, curvature: 0.35 });
  if (!data) return null;
  return (
    <>
      <BaseEdge
        id={props.id}
        path={path}
        style={{ stroke: data.color, strokeWidth: data.width, opacity: data.dim ? 0.12 : 0.9, strokeLinecap: "round" }}
      />
      {data.showLabel && !data.dim && (
        <EdgeLabelRenderer>
          <div className="pm-edge-label" style={{ transform: `translate(-50%, -50%) translate(${lx}px, ${ly}px)` }}>
            {data.label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
});

const nodeTypes = { station: StationNode };
const edgeTypes = { flow: FlowEdge };

function layout(nodes: MapNode[], edges: MapEdge[], vertical: boolean) {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: vertical ? "TB" : "LR", nodesep: 22, ranksep: vertical ? 46 : 64, marginx: 10, marginy: 10 });
  g.setDefaultEdgeLabel(() => ({}));
  nodes.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }));
  // Les arcs les plus fréquents d'abord : dagre les aligne en priorité.
  [...edges].sort((a, b) => b.count - a.count).forEach((e) => g.setEdge(e.source, e.target, { weight: Math.log(e.count + 1) }));
  dagre.layout(g);
  const pos: Record<string, { x: number; y: number }> = {};
  nodes.forEach((n) => {
    const p = g.node(n.id);
    pos[n.id] = { x: p.x - NODE_W / 2, y: p.y - NODE_H / 2 };
  });
  return pos;
}

function perfColor(h: number, p: Palette): string {
  // Échelle séquentielle (une teinte) sur log10(heures) de 0,01 h à 1 000 h.
  const t = Math.min(Math.max((Math.log10(Math.max(h, 0.01)) + 2) / 5, 0), 1);
  return p.seq[Math.min(7, Math.max(2, Math.round(2 + t * 5)))];
}

interface Props {
  maps: Record<ViewKey, PM>;
}

function Inner({ maps }: Props) {
  const palette = usePalette();
  const [view, setView] = useState<ViewKey>("milestones");
  const [mode, setMode] = useState<Mode>("frequency");
  const [threshold, setThreshold] = useState(2);
  const [focus, setFocus] = useState<string | null>(null);
  const [vertical, setVertical] = useState(false);
  const flow = useReactFlow();
  const box = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 640px)");
    const on = () => setVertical(mq.matches);
    on();
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);

  const map = maps[view];
  const total = map.cases;
  const { nodes, edges, hidden } = useMemo(() => {
    const min = (threshold / 100) * total;
    const visibleEdges = map.edges.filter((e) => e.count >= min);
    const used = new Set<string>();
    visibleEdges.forEach((e) => {
      used.add(e.source);
      used.add(e.target);
    });
    const visibleNodes = map.nodes.filter((n) => used.has(n.id));
    const pos = layout(visibleNodes, visibleEdges, vertical);
    const related = new Set<string>();
    if (focus) {
      related.add(focus);
      visibleEdges.forEach((e) => {
        if (e.source === focus) related.add(e.target);
        if (e.target === focus) related.add(e.source);
      });
    }
    const maxCount = Math.max(...visibleEdges.map((e) => e.count), 1);
    const labelMin = maxCount * 0.04;
    const rfNodes: Node<StationData>[] = visibleNodes.map((n) => ({
      id: n.id,
      type: "station",
      position: pos[n.id],
      data: { node: n, dim: !!focus && !related.has(n.id), vertical },
      draggable: false,
    }));
    const rfEdges: Edge<FlowData>[] = visibleEdges.map((e) => {
      const isPerf = mode === "performance" && e.median_h !== undefined;
      const color = isPerf ? perfColor(e.median_h as number, palette) : palette.ink;
      return {
        id: `${e.source}>${e.target}`,
        source: e.source,
        target: e.target,
        type: "flow",
        data: {
          edge: e,
          mode,
          color,
          width: 1.2 + 6 * Math.sqrt(e.count / maxCount),
          label: isPerf ? durationLabel(e.median_h) : num(e.count),
          showLabel: e.count >= labelMin,
          dim: !!focus && e.source !== focus && e.target !== focus,
        },
      };
    });
    return { nodes: rfNodes, edges: rfEdges, hidden: map.edges.length - visibleEdges.length };
  }, [map, total, threshold, mode, focus, vertical, palette]);

  /** Vue de départ lisible : début du processus, zoom ajusté à la hauteur (ou largeur sur mobile). */
  const showStart = useCallback(() => {
    const el = box.current;
    if (!el || !nodes.length) return;
    const xs = nodes.map((n) => n.position.x);
    const ys = nodes.map((n) => n.position.y);
    const minX = Math.min(...xs);
    const minY = Math.min(...ys);
    const spanX = Math.max(...xs) - minX + NODE_W;
    const spanY = Math.max(...ys) - minY + NODE_H;
    const W = el.clientWidth;
    const H = el.clientHeight;
    if (vertical) {
      const zoom = Math.max(0.55, Math.min(1, (W - 24) / spanX));
      flow.setViewport({ x: (W - spanX * zoom) / 2 - minX * zoom, y: 16 - minY * zoom, zoom });
    } else {
      const zoom = Math.max(0.55, Math.min(1, (H - 48) / spanY));
      flow.setViewport({ x: 24 - minX * zoom, y: (H - spanY * zoom) / 2 - minY * zoom, zoom });
    }
  }, [nodes, vertical, flow]);

  useEffect(() => {
    const id = requestAnimationFrame(showStart);
    return () => cancelAnimationFrame(id);
    // Recentrer seulement quand la vue, le seuil ou l'orientation changent.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, threshold, vertical]);

  const focused = focus ? map.nodes.find((n) => n.id === focus) : null;

  return (
    <div className="pm">
      <div className="controls" role="group" aria-label="Réglages de la carte">
        <div className="seg" role="group" aria-label="Vue">
          <button type="button" aria-pressed={view === "milestones"} onClick={() => { setView("milestones"); setFocus(null); }}>
            Jalons
          </button>
          <button type="button" aria-pressed={view === "complete"} onClick={() => { setView("complete"); setFocus(null); }}>
            Avec les tâches
          </button>
        </div>
        <div className="seg" role="group" aria-label="Mesure affichée">
          <button type="button" aria-pressed={mode === "frequency"} onClick={() => setMode("frequency")}>
            Fréquence
          </button>
          <button type="button" aria-pressed={mode === "performance"} onClick={() => setMode("performance")}>
            Performance
          </button>
        </div>
        <div className="seg" role="group" aria-label="Cadrage">
          <button type="button" onClick={showStart}>
            Début
          </button>
          <button type="button" onClick={() => flow.fitView({ padding: 0.06, duration: 300 })}>
            Vue d'ensemble
          </button>
        </div>
        <div className="range">
          <label htmlFor="pm-threshold">
            Liaisons empruntées par au moins <output>{num(threshold)}&nbsp;% des dossiers</output>
          </label>
          <input id="pm-threshold" type="range" min={0} max={20} step={1} value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} />
        </div>
      </div>
      <div className="pm-canvas" ref={box}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          minZoom={0.15}
          maxZoom={2}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable
          onNodeClick={(_, n) => setFocus((f) => (f === n.id ? null : n.id))}
          onPaneClick={() => setFocus(null)}
          proOptions={{ hideAttribution: true }}
          zoomOnScroll={false}
          preventScrolling={false}
          aria-label="Carte de processus interactive"
        >
          <Background color={palette.grid} gap={24} size={1} />
          <Controls showInteractive={false} position="bottom-right" />
        </ReactFlow>
      </div>
      <div className="pm-foot">
        <p className="small muted">
          {mode === "frequency"
            ? "Épaisseur et étiquette : nombre de passages d'une activité à la suivante."
            : "Couleur et étiquette : durée médiane entre deux activités (plus foncé = plus long) ; épaisseur : fréquence."}{" "}
          {hidden > 0 && `${num(hidden)} liaisons rares masquées.`} Faites glisser la carte pour la parcourir ; cliquez sur une station pour isoler ses flux.
        </p>
        {focused && (
          <p className="pm-detail" aria-live="polite">
            <strong>{focused.label}</strong> : {num(focused.count)} occurrences dans {num(focused.cases)} dossiers
            {focused.repeats ? `, dont ${num(focused.repeats)} répétitions immédiates` : ""}
            {focused.median_work_min !== undefined ? ` ; travail médian ${num(focused.median_work_min, 1)} min par session` : ""}
            {focused.median_wait_h !== undefined ? ` ; attente médiane en file ${num(focused.median_wait_h, 1)} h` : ""}.
          </p>
        )}
      </div>
    </div>
  );
}

export default function ProcessMap(props: Props) {
  return (
    <ReactFlowProvider>
      <Inner {...props} />
    </ReactFlowProvider>
  );
}
