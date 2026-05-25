import { useEffect, useMemo, useState } from "react";
import { api, type Me } from "../api/client";
import type { Portfolio, SignalKind, SignalRow } from "../api/types";
import { PortfolioTable } from "../components/PortfolioTable";
import { RulesPanel } from "../components/RulesPanel";
import { DataQualityPanel } from "../components/DataQualityPanel";
import { SignalBadge } from "../components/SignalBadge";

const SIGNALS: SignalKind[] = ["BUY", "SELL", "HOLD"];

export function DashboardView({ me, onLogout }: { me: Me; onLogout: () => void }) {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [scope, setScope] = useState<"global" | number>("global");
  const [rows, setRows] = useState<SignalRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [showRules, setShowRules] = useState(false);
  const [showDQ, setShowDQ] = useState(false);
  const [scoring, setScoring] = useState(false);
  const [filterSignal, setFilterSignal] = useState<SignalKind | "ALL">("ALL");
  const [filterSector, setFilterSector] = useState<string>("ALL");

  useEffect(() => {
    api.portfolios().then((ps) => {
      setPortfolios(ps);
      if (ps.length === 1) setScope(ps[0].id);
    });
  }, []);

  async function refresh() {
    setLoading(true);
    try {
      const data =
        scope === "global" ? await api.globalSignals() : await api.signals(scope);
      setRows(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope]);

  const sectors = useMemo(
    () => ["ALL", ...Array.from(new Set(rows.map((r) => r.sector)))],
    [rows]
  );

  const filtered = rows.filter(
    (r) =>
      (filterSignal === "ALL" || r.signal === filterSignal) &&
      (filterSector === "ALL" || r.sector === filterSector)
  );

  const counts = SIGNALS.map((s) => ({
    s,
    n: rows.filter((r) => r.signal === s).length,
  }));

  async function rescore() {
    setScoring(true);
    try {
      await api.triggerScore();
      await refresh();
    } finally {
      setScoring(false);
    }
  }

  const isGlobal = scope === "global";

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-lg font-bold text-slate-900">Tracknifty</h1>
            <p className="text-xs text-slate-500">BSH Recommendation Engine</p>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-slate-500">
              {me.username} · <span className="uppercase">{me.role}</span>
            </span>
            <button
              onClick={onLogout}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-slate-600 hover:bg-slate-50"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={String(scope)}
              onChange={(e) =>
                setScope(e.target.value === "global" ? "global" : Number(e.target.value))
              }
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
            >
              <option value="global">Global — all portfolios</option>
              {portfolios.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>

            {isGlobal && (
              <>
                <select
                  value={filterSignal}
                  onChange={(e) => setFilterSignal(e.target.value as SignalKind | "ALL")}
                  className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
                >
                  <option value="ALL">All signals</option>
                  {SIGNALS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
                <select
                  value={filterSector}
                  onChange={(e) => setFilterSector(e.target.value)}
                  className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
                >
                  {sectors.map((s) => (
                    <option key={s} value={s}>
                      {s === "ALL" ? "All sectors" : s}
                    </option>
                  ))}
                </select>
              </>
            )}
          </div>

          <div className="flex items-center gap-2">
            {!isGlobal && (
              <button
                onClick={() => setShowRules(true)}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
              >
                Rules & guardrails
              </button>
            )}
            {me.role === "admin" && (
              <>
                <button
                  onClick={() => setShowDQ(true)}
                  className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
                >
                  Data quality
                </button>
                <button
                  onClick={rescore}
                  disabled={scoring}
                  className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50"
                >
                  {scoring ? "Scoring…" : "Re-score"}
                </button>
              </>
            )}
          </div>
        </div>

        <div className="mb-4 flex gap-3">
          {counts.map(({ s, n }) => (
            <div
              key={s}
              className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2"
            >
              <SignalBadge signal={s} small />
              <span className="text-lg font-semibold text-slate-900">{n}</span>
            </div>
          ))}
        </div>

        {loading ? (
          <div className="rounded-lg border border-slate-200 bg-white p-10 text-center text-slate-500">
            Loading signals…
          </div>
        ) : (
          <PortfolioTable rows={filtered} showPortfolio={isGlobal} />
        )}
      </main>

      {showRules && !isGlobal && (
        <RulesPanel
          portfolioId={scope as number}
          onClose={() => setShowRules(false)}
          onSaved={refresh}
        />
      )}
      {showDQ && <DataQualityPanel onClose={() => setShowDQ(false)} />}
    </div>
  );
}
