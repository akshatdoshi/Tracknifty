import { useMemo } from "react";
import type { SignalRow, SignalKind } from "../api/types";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
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
    fontSize: "12px",
  },
};

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <h3 className="mb-4 text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</h3>
      {children}
    </div>
  );
}

function AlertCard({
  label,
  value,
  sub,
  color,
}: {
  label: string;
  value: number;
  sub: string;
  color: string;
}) {
  return (
    <div className={`rounded-xl border p-5 ${color}`}>
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide opacity-70">{label}</div>
      <div className="text-3xl font-bold tabular-nums">{value}</div>
      <div className="mt-0.5 text-xs opacity-60">{sub}</div>
    </div>
  );
}

const HOLDING_BUCKETS = [
  { label: "<30d", min: 0, max: 30 },
  { label: "30-90d", min: 30, max: 90 },
  { label: "90-180d", min: 90, max: 180 },
  { label: "180-365d", min: 180, max: 365 },
  { label: ">365d", min: 365, max: Infinity },
];

export function RiskView({ rows }: { rows: SignalRow[] }) {
  const breachMax = useMemo(() => rows.filter((r) => r.breach_max), [rows]);
  const breachMin = useMemo(() => rows.filter((r) => r.breach_min), [rows]);
  const deriskRows = useMemo(() => rows.filter((r) => r.derisked), [rows]);

  const featureImportance = useMemo(() => {
    const agg: Record<string, number> = {};
    rows.forEach((r) =>
      r.drivers.forEach((d) => {
        agg[d.label] = (agg[d.label] ?? 0) + Math.abs(d.contribution) * 100;
      })
    );
    return Object.entries(agg)
      .map(([label, value]) => ({ label, value: parseFloat(value.toFixed(1)) }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
  }, [rows]);

  const holdingDistribution = useMemo(
    () =>
      HOLDING_BUCKETS.map((b) => ({
        label: b.label,
        count: rows.filter((r) => r.holding_days >= b.min && r.holding_days < b.max).length,
      })),
    [rows]
  );

  if (!rows.length) {
    return <div className="py-20 text-center text-slate-500">No holdings to display.</div>;
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <AlertCard
          label="Breaching Max Weight"
          value={breachMax.length}
          sub="positions above guardrail ceiling"
          color={
            breachMax.length > 0
              ? "border-red-800/60 bg-red-950/40 text-red-300"
              : "border-slate-800 bg-slate-900 text-slate-400"
          }
        />
        <AlertCard
          label="Below Min Weight"
          value={breachMin.length}
          sub="positions below guardrail floor"
          color={
            breachMin.length > 0
              ? "border-amber-800/60 bg-amber-950/40 text-amber-300"
              : "border-slate-800 bg-slate-900 text-slate-400"
          }
        />
        <AlertCard
          label="De-risk Flagged"
          value={deriskRows.length}
          sub="partial exits already taken"
          color={
            deriskRows.length > 0
              ? "border-indigo-800/60 bg-indigo-950/40 text-indigo-300"
              : "border-slate-800 bg-slate-900 text-slate-400"
          }
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="SHAP Feature Importance (Aggregated)">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart layout="vertical" data={featureImportance} margin={{ left: 10, right: 40 }}>
              <CartesianGrid horizontal={false} stroke="#1e293b" />
              <XAxis type="number" tick={{ fill: "#64748b", fontSize: 11 }} />
              <YAxis
                type="category"
                dataKey="label"
                width={160}
                tick={{ fill: "#94a3b8", fontSize: 11 }}
              />
              <Tooltip
                {...TOOLTIP_STYLE}
                formatter={(v: number) => [v.toFixed(1), "Contribution sum"]}
              />
              <Bar dataKey="value" fill="#6366f1" opacity={0.8} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Holding Period Distribution">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={holdingDistribution} margin={{ top: 5, right: 20, bottom: 5 }}>
              <CartesianGrid vertical={false} stroke="#1e293b" />
              <XAxis dataKey="label" tick={{ fill: "#94a3b8", fontSize: 12 }} />
              <YAxis tick={{ fill: "#64748b", fontSize: 11 }} allowDecimals={false} />
              <Tooltip
                {...TOOLTIP_STYLE}
                formatter={(v: number) => [v, "Holdings"]}
              />
              <Bar dataKey="count" fill="#6366f1" opacity={0.7} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card title="Signal Trace Matrix">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500">
                <th className="pb-3 pr-6 font-medium">Stock</th>
                <th className="pb-3 pr-4 font-medium">Portfolio</th>
                <th className="pb-3 pr-6 font-medium">Current Signal</th>
                {["Week -3", "Week -2", "Week -1", "Current"].map((w) => (
                  <th key={w} className="pb-3 px-3 text-center font-medium">
                    {w}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {rows.map((r) => {
                const trace = r.signal_trace;
                const padded = Array.from({ length: 4 }, (_, i) => {
                  const idx = trace.length - 4 + i;
                  return idx >= 0 ? trace[idx] : null;
                });
                return (
                  <tr key={`${r.portfolio_id}:${r.ticker}`} className="hover:bg-slate-800/40">
                    <td className="py-2.5 pr-6 font-medium text-slate-200">{r.ticker}</td>
                    <td className="py-2.5 pr-4 text-slate-500 text-xs">{r.portfolio_name}</td>
                    <td className="py-2.5 pr-6">
                      <SignalBadge signal={r.signal} />
                    </td>
                    {padded.map((s, i) => (
                      <td key={i} className="px-3 py-2.5 text-center">
                        {s ? (
                          <span
                            className="inline-block h-3 w-3 rounded-full"
                            style={{ backgroundColor: SIGNAL_COLORS[s] }}
                            title={s}
                          />
                        ) : (
                          <span className="text-slate-700">·</span>
                        )}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      {(breachMax.length > 0 || breachMin.length > 0 || deriskRows.length > 0) && (
        <Card title="Flagged Positions Detail">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500">
                  <th className="pb-3 pr-6 font-medium">Stock</th>
                  <th className="pb-3 pr-4 font-medium">Signal</th>
                  <th className="pb-3 pr-4 font-medium">Weight</th>
                  <th className="pb-3 pr-4 font-medium">Flag</th>
                  <th className="pb-3 font-medium">Guardrail notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {rows
                  .filter((r) => r.breach_max || r.breach_min || r.derisked)
                  .map((r) => (
                    <tr key={`${r.portfolio_id}:${r.ticker}`} className="hover:bg-slate-800/40">
                      <td className="py-2.5 pr-6 font-medium text-slate-200">{r.ticker}</td>
                      <td className="py-2.5 pr-4">
                        <SignalBadge signal={r.signal} />
                      </td>
                      <td className="py-2.5 pr-4 tabular-nums text-slate-300">
                        {r.weight_pct.toFixed(2)}%
                      </td>
                      <td className="py-2.5 pr-4">
                        {r.breach_max && (
                          <span className="rounded bg-red-900/40 px-1.5 py-0.5 text-xs text-red-400">
                            Over max
                          </span>
                        )}
                        {r.breach_min && (
                          <span className="rounded bg-amber-900/40 px-1.5 py-0.5 text-xs text-amber-400">
                            Under min
                          </span>
                        )}
                        {r.derisked && (
                          <span className="ml-1 rounded bg-indigo-900/40 px-1.5 py-0.5 text-xs text-indigo-400">
                            De-risked
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 text-xs text-slate-500">
                        {r.rule_notes.join(" · ") || "—"}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
