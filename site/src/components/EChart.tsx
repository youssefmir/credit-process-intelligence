import { BarChart, CustomChart, HeatmapChart, LineChart, ScatterChart } from "echarts/charts";
import {
  GraphicComponent,
  GridComponent,
  MarkAreaComponent,
  MarkLineComponent,
  MarkPointComponent,
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import type { EChartsCoreOption } from "echarts/core";
import { SVGRenderer } from "echarts/renderers";
import { useEffect, useRef } from "react";

import { useInViewOnce, useReducedMotion } from "../lib/motion";
import { usePalette, type Palette } from "../lib/theme";

echarts.use([
  BarChart,
  LineChart,
  ScatterChart,
  HeatmapChart,
  CustomChart,
  GridComponent,
  TooltipComponent,
  MarkLineComponent,
  MarkAreaComponent,
  MarkPointComponent,
  GraphicComponent,
  VisualMapComponent,
  SVGRenderer,
]);

export type OptionBuilder = (p: Palette, ctx: { width: number }) => EChartsCoreOption;

interface Props {
  build: OptionBuilder;
  height: number;
  label: string;
  /** Dépendances supplémentaires qui doivent redessiner le graphique. */
  deps?: unknown[];
}

const FONT = '"Archivo Variable", "Archivo", sans-serif';

/** Options communes : typographie, infobulle sobre, grille discrète, animation au défilement. */
export function baseOption(p: Palette, reduced: boolean): EChartsCoreOption {
  return {
    animation: !reduced,
    animationDuration: 600,
    animationEasing: "cubicOut",
    animationDurationUpdate: 400,
    textStyle: { fontFamily: FONT, color: p.muted, fontSize: 12 },
    tooltip: {
      trigger: "item",
      backgroundColor: p.bg,
      borderColor: p.ink,
      borderWidth: 1.5,
      padding: [8, 10],
      textStyle: { color: p.ink, fontFamily: FONT, fontSize: 13 },
      extraCssText: "border-radius:0;box-shadow:none;",
    },
  };
}

export function axisCommon(p: Palette) {
  return {
    axisLine: { lineStyle: { color: p.context, width: 1 } },
    axisTick: { show: false },
    axisLabel: { color: p.muted, fontFamily: FONT, fontSize: 12 },
    splitLine: { lineStyle: { color: p.grid, width: 1, type: "solid" as const } },
    nameTextStyle: { color: p.muted, fontFamily: FONT, fontSize: 12 },
  };
}

export default function EChart({ build, height, label, deps = [] }: Props) {
  const { ref, seen } = useInViewOnce<HTMLDivElement>();
  const chartRef = useRef<echarts.ECharts | null>(null);
  const palette = usePalette();
  const reduced = useReducedMotion();

  useEffect(() => {
    const el = ref.current;
    if (!el || !seen) return;
    const chart = echarts.init(el, undefined, { renderer: "svg" });
    chartRef.current = chart;
    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(el);
    return () => {
      ro.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, [seen, ref]);

  useEffect(() => {
    const chart = chartRef.current;
    const el = ref.current;
    if (!chart || !el) return;
    const opt = build(palette, { width: el.clientWidth });
    chart.setOption({ ...baseOption(palette, reduced), ...opt }, { notMerge: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seen, palette, reduced, build, ...deps]);

  return <div ref={ref} className="chart-box" style={{ height }} role="img" aria-label={label} />;
}
