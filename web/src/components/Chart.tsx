/**
 * Thin React wrapper over ECharts.
 *
 * Only the chart types and components the dashboard uses are registered, so
 * tree-shaking keeps the echarts chunk well below a full build.
 */

import { BarChart, BoxplotChart, CustomChart, RadarChart, ScatterChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useRef } from "react";

import { useTheme } from "../state/useTheme";

echarts.use([
  BarChart,
  BoxplotChart,
  CustomChart,
  RadarChart,
  ScatterChart,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
  CanvasRenderer,
]);

export type ChartOption = Parameters<echarts.ECharts["setOption"]>[0];

interface ChartProps {
  option: ChartOption;
  /** CSS height. Charts are always full-width of their container. */
  height?: number | string;
  ariaLabel: string;
}

export function Chart({ option, height = 340, ariaLabel }: ChartProps) {
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<echarts.ECharts | null>(null);
  const { resolved } = useTheme();

  useEffect(() => {
    if (!container.current) return;

    const chart = echarts.init(container.current, undefined, {
      renderer: "canvas",
    });
    instance.current = chart;

    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(container.current);

    return () => {
      observer.disconnect();
      chart.dispose();
      instance.current = null;
    };
    // Re-created on theme change so axis and label colours are recomputed.
  }, [resolved]);

  useEffect(() => {
    // `notMerge` avoids stale series lingering when a filter changes the shape
    // of the data (e.g. fewer categories than the previous render).
    instance.current?.setOption(option, { notMerge: true });
  }, [option]);

  return (
    <div
      ref={container}
      className="chart"
      style={{ height: typeof height === "number" ? `${height}px` : height }}
      role="img"
      aria-label={ariaLabel}
    />
  );
}
