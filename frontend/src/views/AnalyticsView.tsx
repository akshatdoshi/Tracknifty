import { useMemo } from "react";
import type { SignalRow, SignalKind } from "../api/types";
import {
  ScatterChart,
  Scatter,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
  LabelList,
} from "recharts";

const SIGNAL_COLORS: Record<SignalKind, string> = {
  BUY: "#22c55e",
  SELL: "#ef4444",
  HOLD: "#f59e0b",
};

const TOOLTIP_STYLE = {
  contentStyle: {
    backgroundColor: "#1e293b",
    border: "1px solid #334155",
    borderRadius: "8px",
    color: "#f1f5f9",
    fontSize: "12px",
  },
};

function Card({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</div>
      {subtitle && <div className="mb-4 text-xs text-slate-600">{subtitle}</div>}
      {!subtitle && <div className="mb-4" />}
      {children}
    </div>
  );
}

type ScatterPoint = {
  ticker: string;
  x: number;
  y: number;
  signal: SignalKind;
};

export function AnalyticsView({ rows }: { rows: SignalRow[] }) {
  const scatterData = useMemo(
    () =>
      rows
        .filter((r) => r.ret_1m_pct !== null && r.alpha_pct !== null)
        .map((r) => ({
          ticker: r.ticker,
          x: parseFloat((r.ret_1m_pct as number).toFixed(2)),
          y: parseFloat((r.alpha_pct as number).toFixed(2)),
          signal: r.signal,
        })),
    [rows]
  );

  const scatterBySignal = useMemo(() => {
    const map: Record<SignalKind, ScatterPoint[]> = { BUY: [], SELL: [], HOLD: [] };
    scatterData.forEach((d) => map[d.signal].push(d));
    return map;
  }, [scatterData]);

  const returnData = useMemo(
    () =>
      rows
        .filter((r) => r.ret_1m_pct !== null)
        .map((r) => ({ ticker: r.ticker, value: parseFloat((r.ret_1m_pct as number).toFixed(2)), signal: r.signal }))
        .sort((a, b) => b.value - a.value),
    [rows]
  );

  const confidenceData = useMemo(
    () =>
      [...rows]
        .sort((a, b) => b.confidence - a.confidence)
        .map((r) => ({ ticker: r.ticker, value: parseFloat(r.confidence.toFixed(1)), signal: r.signal })),
    [rows]
  );

  const pnlData = useMemo(
    () =>
      rows
        .filter((r) => r.unrealised_pnl_pct !== null)
        .map((r) => ({ ticker: r.ticker, value: parseFloat((r.unrealised_pnl_pct as number).toFixed(2)), signal: r.signal }))
        .sort((a, b) => b.value - a.value),
    [rows]
  );

  if (!rows.length) {
    return <div className="py-20 text-center text-slate-500">No holdings to display.</div>;
  }

  const barHeight = Math.max(200, rows.length * 36);

  return (
    <div className="space-y-6">
      <Card title="Return vs Alpha" subtitle="1M return (x) vs alpha over benchmark (y) · colored by signal">
        <ResponsiveContainer width="100%" height={320}>
          <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 0 }}>
            <CartesianGrid stroke="#1e293b" />
            <XAxis
              type="number"
              dataKey="x"
              name="1M Return"
              tick={{ fill: "#64748b", fontSize: 11 }}
              tickFormatter={(v) => `${v}%`}
              label={{ value: "1M Return %", position: "insideBottom", offset: -10, fill: "#64748b", fontSize: 11 }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="Alpha"
              tick={{ fill: "#64748b", fontSize: 11 }}
              tickFormatter={(v) => `${v}%`}
              label={{ value: "Alpha %", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 11 }}
            />
            <ReferenceLine x={0} stroke="#334155" strokeDasharray="4 2" />
            <ReferenceLine y={0} stroke="#334155" strokeDasharray="4 2" />
            <Tooltip
              {...TOOLTIP_STYLE}
              cursor={{ stroke: "#475569" }}
              content={({ payload }) => {
                if (!payload?.length) return null;
                const d = payload[0].payload as ScatterPoint;
                return (
                  <div style={TOOLTIP_STYLE.contentStyle}>
                    <div className="font-semibold">{d.ticker}</div>
                    <div>Signal: {d.signal}</div>
                    <div>1M Return: {d.x}%</div>
                    <div>Alpha: {d.y}%</div>
                  </div>
                );
              }}
            />
            {(["BUY", "SELL", "HOLD"] as SignalKind[]).map((s) => (
              <Scatter
                key={s}
                name={s}
                data={scatterBySignal[s]}
                fill={SIGNAL_COLORS[s]}
                opacity={0.85}
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
        <div className="mt-2 flex items-center gap-4">
          {(["BUY", "SELL", "HOLD"] as SignalKind[]).map((s) => (
            <div key={s} className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: SIGNAL_COLORS[s] }} />
              <span className="text-xs text-slate-400">{s}</span>
            </div>
          ))}
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="1M Returns by Stock" subtitle="Sorted descending">
          <ResponsiveContainer width="100%" height={barHeight}>
            <BarChart layout="vertical" data={returnData} margin={{ left: 10, right: 40 }}>
              <CartesianGrid horizontal={false} stroke="#1e293b" />
              <XAxis type="number" tick={{ fill: "#64748b", fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
              <YAxis type="category" dataKey="ticker" width={90} tick={{ fill: "#94a3b8", fontSize: 12 }} />
              <ReferenceLine x={0} stroke="#475569" />
              <Tooltip
                {...TOOLTIP_STYLE}
                formatter={(v: number) => [`${v}%`, "1M Return"]}
              />
              <Bar dataKey="value" radius={[0, 3, 3, 0]}>
                <LabelList
                  dataKey="value"
                  position="right"
                  formatter={(v: number) => `${v > 0 ? "+" : ""}${v}%`}
                  style={{ fontSize: 11, fill: "#64748b" }}
                />
                {returnData.map((d) => (
                  <Cell key={d.ticker} fill={d.value >= 0 ? "#22c55e" : "#ef4444"} opacity={0.8} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Confidence by Stock" subtitle="Colored by signal">
          <ResponsiveContainer width="100%" height={barHeight}>
            <BarChart layout="vertical" data={confidenceData} margin={{ left: 10, right: 50 }}>
              <CartesianGrid horizontal={false} stroke="#1e293b" />
              <XAxis type="number" domain={[0, 100]} tick={{ fill: "#64748b", fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
              <YAxis type="category" dataKey="ticker" width={90} tick={{ fill: "#94a3b8", fontSize: 12 }} />
              <Tooltip
                {...TOOLTIP_STYLE}
                formatter={(v: number) => [`${v}%`, "Confidence"]}
              />
              <Bar dataKey="value" radius={[0, 3, 3, 0]}>
                <LabelList
                  dataKey="value"
                  position="right"
                  formatter={(v: number) => `${v}%`}
                  style={{ fontSize: 11, fill: "#64748b" }}
                />
                {confidenceData.map((d) => (
                  <Cell key={d.ticker} fill={SIGNAL_COLORS[d.signal]} opacity={0.75} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {pnlData.length > 0 && (
        <Card title="Unrealised P&L by Stock" subtitle="Percentage gain/loss from weighted average cost">
          <ResponsiveContainer width="100%" height={barHeight}>
            <BarChart layout="vertical" data={pnlData} margin={{ left: 10, right: 50 }}>
              <CartesianGrid horizontal={false} stroke="#1e293b" />
              <XAxis type="number" tick={{ fill: "#64748b", fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
              <YAxis type="category" dataKey="ticker" width={90} tick={{ fill: "#94a3b8", fontSize: 12 }} />
              <ReferenceLine x={0} stroke="#475569" />
              <Tooltip
                {...TOOLTIP_STYLE}
                formatter={(v: number) => [`${v > 0 ? "+" : ""}${v}%`, "Unrealised P&L"]}
              />
              <Bar dataKey="value" radius={[0, 3, 3, 0]}>
                <LabelList
                  dataKey="value"
                  position="right"
                  formatter={(v: number) => `${v > 0 ? "+" : ""}${v}%`}
                  style={{ fontSize: 11, fill: "#64748b" }}
                />
                {pnlData.map((d) => (
                  <Cell key={d.ticker} fill={d.value >= 0 ? "#22c55e" : "#ef4444"} opacity={0.8} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}
    </div>
  );
}
