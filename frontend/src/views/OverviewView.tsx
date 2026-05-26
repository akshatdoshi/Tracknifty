import { useMemo } from "react";
import type { SignalRow, SignalKind } from "../api/types";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { SignalBadge } from "../components/SignalBadge";

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
  },
};

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <h3 className="mb-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </h3>
      {children}
    </div>
  );
}

function KpiCard({
  label,
  value,
  sub,
  color,
}: {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className={`text-2xl font-bold tabular-nums ${color ?? "text-slate-100"}`}>
        {value}
      </div>
      {sub && <div className="mt-0.5 text-xs text-slate-500">{sub}</div>}
    </div>
  );
}

export function OverviewView({ rows }: { rows: SignalRow[] }) {
  const signalCounts = useMemo(() => {
    const counts = { BUY: 0, SELL: 0, HOLD: 0 };
    rows.forEach((r) => counts[r.signal]++);
    return (["BUY", "SELL", "HOLD"] as SignalKind[]).map((s) => ({
      name: s,
      value: counts[s],
    }));
  }, [rows]);

  const avgConfidence = useMemo(() => {
    if (!rows.length) return 0;
    return rows.reduce((s, r) => s + r.confidence, 0) / rows.length;
  }, [rows]);

  const weightedPnl = useMemo(() => {
    const valid = rows.filter((r) => r.unrealised_pnl_pct !== null);
    if (!valid.length) return null;
    const totalW = valid.reduce((s, r) => s + r.weight_pct, 0);
    if (!totalW) return null;
    return valid.reduce((s, r) => s + (r.unrealised_pnl_pct! * r.weight_pct) / totalW, 0);
  }, [rows]);

  const deriskCount = useMemo(() => rows.filter((r) => r.derisked).length, [rows]);

  const sectorData = useMemo(() => {
    const map: Record<string, { weight: number; signals: Record<SignalKind, number> }> = {};
    rows.forEach((r) => {
      if (!map[r.sector]) map[r.sector] = { weight: 0, signals: { BUY: 0, SELL: 0, HOLD: 0 } };
      map[r.sector].weight += r.weight_pct;
      map[r.sector].signals[r.signal]++;
    });
    return Object.entries(map)
      .map(([sector, { weight, signals }]) => {
        const dominant = (["BUY", "SELL", "HOLD"] as SignalKind[]).reduce(
          (a, b) => (signals[a] >= signals[b] ? a : b),
          "HOLD" as SignalKind
        );
        return { sector, weight: parseFloat(weight.toFixed(2)), dominant };
      })
      .sort((a, b) => b.weight - a.weight);
  }, [rows]);

  const topHoldings = useMemo(
    () => [...rows].sort((a, b) => b.weight_pct - a.weight_pct).slice(0, 8),
    [rows]
  );

  if (!rows.length) {
    return (
      <div className="py-20 text-center text-slate-500">No holdings to display.</div>
    );
  }

  const pnlColor =
    weightedPnl === null
      ? "text-slate-400"
      : weightedPnl >= 0
      ? "text-green-400"
      : "text-red-400";

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <KpiCard label="Holdings" value={rows.length} sub="active positions" />
        <KpiCard
          label="Avg Confidence"
          value={`${avgConfidence.toFixed(1)}%`}
          sub="model confidence"
          color={avgConfidence >= 75 ? "text-green-400" : avgConfidence >= 60 ? "text-amber-400" : "text-slate-300"}
        />
        <KpiCard
          label="Weighted P&L"
          value={weightedPnl === null ? "—" : `${weightedPnl >= 0 ? "+" : ""}${weightedPnl.toFixed(2)}%`}
          sub="unrealised, weight-adjusted"
          color={pnlColor}
        />
        <KpiCard
          label="De-risk Flags"
          value={deriskCount}
          sub={`of ${rows.length} holdings`}
          color={deriskCount > 0 ? "text-amber-400" : "text-slate-100"}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Signal Mix">
          <div className="flex items-center gap-6">
            <ResponsiveContainer width={180} height={180}>
              <PieChart>
                <Pie
                  data={signalCounts}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {signalCounts.map((entry) => (
                    <Cell key={entry.name} fill={SIGNAL_COLORS[entry.name as SignalKind]} />
                  ))}
                </Pie>
                <Tooltip
                  {...TOOLTIP_STYLE}
                  formatter={(v: number) => [v, "Holdings"]}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-3">
              {signalCounts.map(({ name, value }) => (
                <div key={name} className="flex items-center gap-3">
                  <SignalBadge signal={name as SignalKind} />
                  <span className="text-xl font-bold tabular-nums text-slate-100">{value}</span>
                  <span className="text-xs text-slate-500">
                    ({rows.length ? Math.round((value / rows.length) * 100) : 0}%)
                  </span>
                </div>
              ))}
            </div>
          </div>
        </Card>

        <Card title="Weight by Sector">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              layout="vertical"
              data={sectorData}
              margin={{ left: 10, right: 30 }}
            >
              <CartesianGrid horizontal={false} stroke="#1e293b" />
              <XAxis
                type="number"
                tick={{ fill: "#64748b", fontSize: 11 }}
                tickFormatter={(v) => `${v}%`}
              />
              <YAxis
                type="category"
                dataKey="sector"
                width={80}
                tick={{ fill: "#94a3b8", fontSize: 12 }}
              />
              <Tooltip
                {...TOOLTIP_STYLE}
                formatter={(v: number) => [`${v}%`, "Weight"]}
              />
              <Bar dataKey="weight" radius={[0, 4, 4, 0]}>
                {sectorData.map((entry) => (
                  <Cell key={entry.sector} fill={SIGNAL_COLORS[entry.dominant]} opacity={0.8} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card title="Top Holdings by Weight">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart
            layout="vertical"
            data={topHoldings.map((r) => ({
              ticker: r.ticker,
              weight: parseFloat(r.weight_pct.toFixed(2)),
              signal: r.signal,
            }))}
            margin={{ left: 10, right: 50 }}
          >
            <CartesianGrid horizontal={false} stroke="#1e293b" />
            <XAxis
              type="number"
              tick={{ fill: "#64748b", fontSize: 11 }}
              tickFormatter={(v) => `${v}%`}
            />
            <YAxis
              type="category"
              dataKey="ticker"
              width={100}
              tick={{ fill: "#94a3b8", fontSize: 12 }}
            />
            <Tooltip
              {...TOOLTIP_STYLE}
              formatter={(v: number, _name, props) => [
                `${v}% · ${(props.payload as { signal: string }).signal}`,
                "Weight",
              ]}
            />
            <Bar
              dataKey="weight"
              radius={[0, 4, 4, 0]}
              label={{ position: "right", formatter: (v: number) => `${v}%`, fontSize: 11, fill: "#64748b" }}
            >
              {topHoldings.map((r) => (
                <Cell key={r.ticker} fill={SIGNAL_COLORS[r.signal]} opacity={0.75} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
}
