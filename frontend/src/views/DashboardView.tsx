import { useEffect, useMemo, useState } from "react";
import { api, type Me } from "../api/client";
import type { Portfolio, SignalKind, SignalRow } from "../api/types";
import { PortfolioTable } from "../components/PortfolioTable";
import { RulesPanel } from "../components/RulesPanel";
import { DataQualityPanel } from "../components/DataQualityPanel";
import { SignalBadge } from "../components/SignalBadge";
import { OverviewView } from "./OverviewView";
import { AnalyticsView } from "./AnalyticsView";
import { RiskView } from "./RiskView";

type View = "overview" | "holdings" | "analytics" | "risk";

const SIGNALS: SignalKind[] = ["BUY", "SELL", "HOLD"];

function IconOverview() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
      <rect x="3" y="13" width="4" height="8" rx="1" />
      <rect x="10" y="9" width="4" height="12" rx="1" />
      <rect x="17" y="5" width="4" height="16" rx="1" />
    </svg>
  );
}

function IconHoldings() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <line x1="3" y1="9" x2="21" y2="9" />
      <line x1="3" y1="14" x2="21" y2="14" />
      <line x1="9" y1="9" x2="9" y2="20" />
    </svg>
  );
}

function IconAnalytics() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  );
}

function IconRisk() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
      <path d="M12 2L3 7v6c0 5 4 9.27 9 10 5-.73 9-5 9-10V7L12 2z" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <circle cx="12" cy="15" r="0.5" fill="currentColor" />
    </svg>
  );
}

function IconSettings() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

function IconDatabase() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
    </svg>
  );
}

function IconRefresh() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
      <polyline points="23 4 23 10 17 10" />
      <polyline points="1 20 1 14 7 14" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  );
}

const NAV_ITEMS: { id: View; label: string; Icon: () => JSX.Element }[] = [
  { id: "overview", label: "Overview", Icon: IconOverview },
  { id: "holdings", label: "Holdings", Icon: IconHoldings },
  { id: "analytics", label: "Analytics", Icon: IconAnalytics },
  { id: "risk", label: "Risk", Icon: IconRisk },
];

const VIEW_TITLES: Record<View, string> = {
  overview: "Portfolio Overview",
  holdings: "Holdings Table",
  analytics: "Performance Analytics",
  risk: "Risk Dashboard",
};

export function DashboardView({ me, onLogout }: { me: Me; onLogout: () => void }) {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [scope, setScope] = useState<"global" | number>("global");
  const [rows, setRows] = useState<SignalRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState<View>("overview");
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
        scope === "global" ? await api.globalSignals() : await api.signals(scope as number);
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

  function NavItem({ id, label, Icon }: { id: View; label: string; Icon: () => JSX.Element }) {
    const active = activeView === id;
    return (
      <button
        onClick={() => setActiveView(id)}
        className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors ${
          active
            ? "bg-slate-800 text-slate-100 font-medium"
            : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
        }`}
      >
        <Icon />
        {label}
      </button>
    );
  }

  return (
    <div className="flex min-h-screen bg-slate-950">
      <aside className="fixed left-0 top-0 flex h-full w-56 flex-col border-r border-slate-800 bg-slate-900">
        <div className="p-5 pb-4">
          <div className="text-lg font-bold text-indigo-400">Tracknifty</div>
          <div className="text-xs text-slate-600">BSH Engine</div>
        </div>

        <div className="px-3 pb-4">
          <select
            value={String(scope)}
            onChange={(e) => {
              setFilterSignal("ALL");
              setFilterSector("ALL");
              setScope(e.target.value === "global" ? "global" : Number(e.target.value));
            }}
            className="w-full rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5 text-xs text-slate-300 focus:border-indigo-500 focus:outline-none"
          >
            <option value="global">Global — all portfolios</option>
            {portfolios.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        <nav className="flex-1 space-y-0.5 px-3">
          {NAV_ITEMS.map((item) => (
            <NavItem key={item.id} {...item} />
          ))}

          <div className="my-3 border-t border-slate-800" />

          {!isGlobal && (
            <button
              onClick={() => setShowRules(true)}
              className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
            >
              <IconSettings />
              Rules & Guardrails
            </button>
          )}
          {me.role === "admin" && (
            <>
              <button
                onClick={() => setShowDQ(true)}
                className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
              >
                <IconDatabase />
                Data Quality
              </button>
              <button
                onClick={rescore}
                disabled={scoring}
                className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 disabled:opacity-50"
              >
                <IconRefresh />
                {scoring ? "Scoring…" : "Re-score"}
              </button>
            </>
          )}
        </nav>

        <div className="border-t border-slate-800 p-4">
          <div className="mb-2 text-xs text-slate-500">
            {me.username}{" "}
            <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-slate-400">
              {me.role}
            </span>
          </div>
          <button
            onClick={onLogout}
            className="w-full rounded-md border border-slate-700 px-3 py-1.5 text-xs text-slate-400 hover:bg-slate-800 hover:text-slate-200"
          >
            Logout
          </button>
        </div>
      </aside>

      <main className="ml-56 flex-1 p-6">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-100">{VIEW_TITLES[activeView]}</h2>
            <p className="text-xs text-slate-500">
              {isGlobal ? "All portfolios" : portfolios.find((p) => p.id === scope)?.name ?? ""}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {counts.map(({ s, n }) => (
              <div
                key={s}
                className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5"
              >
                <SignalBadge signal={s} small />
                <span className="text-sm font-semibold tabular-nums text-slate-100">{n}</span>
              </div>
            ))}
          </div>
        </div>

        {activeView === "holdings" && (
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <select
              value={filterSignal}
              onChange={(e) => setFilterSignal(e.target.value as SignalKind | "ALL")}
              className="rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-slate-300 focus:border-indigo-500 focus:outline-none"
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
              className="rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-slate-300 focus:border-indigo-500 focus:outline-none"
            >
              {sectors.map((s) => (
                <option key={s} value={s}>
                  {s === "ALL" ? "All sectors" : s}
                </option>
              ))}
            </select>
          </div>
        )}

        {loading ? (
          <div className="flex h-64 items-center justify-center">
            <div className="text-slate-500">Loading signals…</div>
          </div>
        ) : (
          <>
            {activeView === "overview" && <OverviewView rows={rows} />}
            {activeView === "holdings" && (
              <PortfolioTable rows={filtered} showPortfolio={isGlobal} />
            )}
            {activeView === "analytics" && <AnalyticsView rows={rows} />}
            {activeView === "risk" && <RiskView rows={rows} />}
          </>
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
