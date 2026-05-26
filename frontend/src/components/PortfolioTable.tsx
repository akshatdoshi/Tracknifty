import { Fragment, useState } from "react";
import type { SignalRow } from "../api/types";
import { ConfidenceBar } from "./ConfidenceBar";
import { DetailPanel } from "./DetailPanel";
import { SignalBadge } from "./SignalBadge";

function pctClass(v: number | null) {
  if (v === null || v === undefined) return "text-slate-500";
  return v >= 0 ? "text-green-400" : "text-red-400";
}
function pct(v: number | null) {
  return v === null || v === undefined ? "—" : `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

export function PortfolioTable({
  rows,
  showPortfolio,
}: {
  rows: SignalRow[];
  showPortfolio?: boolean;
}) {
  const [openKey, setOpenKey] = useState<string | null>(null);

  if (!rows.length) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-10 text-center text-slate-500">
        No holdings to display.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-800 bg-slate-900 shadow-sm">
      <table className="min-w-full divide-y divide-slate-800 text-sm">
        <thead className="bg-slate-800 text-left text-xs uppercase tracking-wide text-slate-400">
          <tr>
            <th className="px-6 py-3">Stock</th>
            {showPortfolio && <th className="px-4 py-3">Portfolio</th>}
            <th className="px-4 py-3">Weight</th>
            <th className="px-4 py-3">1M return</th>
            <th className="px-4 py-3">vs Benchmark</th>
            <th className="px-4 py-3">Confidence</th>
            <th className="px-4 py-3">Signal</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {rows.map((row) => {
            const key = `${row.portfolio_id}:${row.ticker}`;
            const open = openKey === key;
            return (
              <Fragment key={key}>
                <tr
                  className={`cursor-pointer border-slate-800 hover:bg-slate-800/60 ${open ? "bg-slate-800/60" : ""}`}
                  onClick={() => setOpenKey(open ? null : key)}
                >
                  <td className="px-6 py-3">
                    <div className="font-medium text-slate-100">{row.ticker}</div>
                    <div className="text-xs text-slate-500">{row.sector}</div>
                  </td>
                  {showPortfolio && (
                    <td className="px-4 py-3 text-slate-300">{row.portfolio_name}</td>
                  )}
                  <td className="px-4 py-3">
                    <span
                      className={`tabular-nums ${
                        row.breach_max
                          ? "rounded bg-red-900/40 px-1.5 py-0.5 font-medium text-red-400"
                          : row.breach_min
                          ? "rounded bg-amber-900/40 px-1.5 py-0.5 font-medium text-amber-400"
                          : "text-slate-300"
                      }`}
                      title={
                        row.breach_max
                          ? "Above max-weight guardrail"
                          : row.breach_min
                          ? "Below min-weight guardrail"
                          : ""
                      }
                    >
                      {row.weight_pct.toFixed(2)}%
                    </span>
                  </td>
                  <td className={`px-4 py-3 tabular-nums ${pctClass(row.ret_1m_pct)}`}>
                    {pct(row.ret_1m_pct)}
                  </td>
                  <td className={`px-4 py-3 tabular-nums ${pctClass(row.alpha_pct)}`}>
                    {pct(row.alpha_pct)}
                  </td>
                  <td className="px-4 py-3">
                    <ConfidenceBar value={row.confidence} />
                  </td>
                  <td className="px-4 py-3">
                    <SignalBadge signal={row.signal} />
                  </td>
                </tr>
                {open && (
                  <tr>
                    <td colSpan={showPortfolio ? 7 : 6} className="p-0">
                      <DetailPanel row={row} />
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
