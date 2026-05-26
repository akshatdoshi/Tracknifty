import type { SignalKind } from "../api/types";

const DOT: Record<SignalKind, string> = {
  BUY: "bg-green-500",
  SELL: "bg-red-500",
  HOLD: "bg-amber-500",
};

export function SignalTrace({ trace }: { trace: SignalKind[] }) {
  if (!trace.length) return <span className="text-xs text-slate-400">—</span>;
  return (
    <div className="flex items-center gap-1">
      {trace.map((s, i) => (
        <div key={i} className="flex items-center gap-1">
          <span
            title={s}
            className={`inline-block h-2.5 w-2.5 rounded-full ${DOT[s]}`}
          />
          {i < trace.length - 1 && <span className="text-slate-600">›</span>}
        </div>
      ))}
    </div>
  );
}
