export function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  const color =
    pct >= 75 ? "bg-green-500" : pct >= 60 ? "bg-amber-500" : "bg-slate-600";
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-20 overflow-hidden rounded-full bg-slate-800">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-9 text-right text-xs tabular-nums text-slate-300">
        {pct.toFixed(0)}%
      </span>
    </div>
  );
}
