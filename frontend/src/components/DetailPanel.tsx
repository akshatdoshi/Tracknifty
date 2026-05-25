import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SignalRow } from "../api/types";
import { SignalTrace } from "./SignalTrace";

function fmt(value: number | null, suffix = "") {
  return value === null || value === undefined ? "—" : `${value.toFixed(2)}${suffix}`;
}

export function DetailPanel({ row }: { row: SignalRow }) {
  const chartData = row.drivers.map((d) => ({
    label: d.label,
    value: Math.round(d.contribution * 100),
    direction: d.direction,
  }));

  return (
    <div className="grid grid-cols-1 gap-6 border-t border-slate-200 bg-slate-50 px-6 py-5 md:grid-cols-3">
      <div className="md:col-span-2">
        <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Why this signal — SHAP drivers
        </h4>
        <p className="mb-3 text-sm text-slate-700">{row.explanation || "No explanation available."}</p>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={Math.max(120, chartData.length * 38)}>
            <BarChart layout="vertical" data={chartData} margin={{ left: 20, right: 30 }}>
              <XAxis type="number" hide domain={[0, 100]} />
              <YAxis
                type="category"
                dataKey="label"
                width={180}
                tick={{ fontSize: 12, fill: "#475569" }}
              />
              <Tooltip formatter={(v: number) => [`${v}%`, "Contribution"]} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]} label={{ position: "right", formatter: (v: number) => `${v}%`, fontSize: 11 }}>
                {chartData.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={
                      entry.direction === "Positive"
                        ? "#16a34a"
                        : entry.direction === "Negative"
                        ? "#dc2626"
                        : "#94a3b8"
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-slate-400">No driver data — run scoring first.</p>
        )}

        {row.rule_notes.length > 0 && (
          <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3">
            <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-amber-700">
              Guardrails applied
            </div>
            <ul className="list-inside list-disc space-y-0.5 text-xs text-amber-800">
              {row.rule_notes.map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Position summary
        </h4>
        <dl className="space-y-1.5 text-sm">
          <Row label="Carrying cost (WAC)" value={fmt(row.wac)} />
          <Row label="Current price" value={fmt(row.current_price)} />
          <Row
            label="Unrealised P&L"
            value={fmt(row.unrealised_pnl_pct, "%")}
            tone={(row.unrealised_pnl_pct ?? 0) >= 0 ? "pos" : "neg"}
          />
          <Row label="Quantity" value={row.quantity.toLocaleString()} />
          <Row label="Holding period" value={`${row.holding_days} days`} />
          <Row label="De-risk status" value={row.derisked ? "Partial exit done" : "None"} />
          {row.raw_signal !== row.signal && (
            <Row label="Model (pre-rules)" value={row.raw_signal} />
          )}
        </dl>
        <h4 className="mb-1 mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Weekly signal trace
        </h4>
        <SignalTrace trace={row.signal_trace} />
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "pos" | "neg";
}) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-slate-500">{label}</dt>
      <dd
        className={`font-medium tabular-nums ${
          tone === "pos" ? "text-green-600" : tone === "neg" ? "text-red-600" : "text-slate-800"
        }`}
      >
        {value}
      </dd>
    </div>
  );
}
