import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { DataQuality } from "../api/types";

export function DataQualityPanel({ onClose }: { onClose: () => void }) {
  const [dq, setDq] = useState<DataQuality | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.dataQuality().then(setDq).catch((e) => setErr((e as Error).message));
  }, []);

  return (
    <div className="fixed inset-0 z-20 flex justify-end bg-black/60" onClick={onClose}>
      <div
        className="h-full w-full max-w-md overflow-y-auto border-l border-slate-800 bg-slate-900 p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-100">Data Quality</h3>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300">
            ✕
          </button>
        </div>
        {err && <p className="text-sm text-red-400">{err}</p>}
        {dq && (
          <div className="space-y-6">
            <div className="grid grid-cols-3 gap-3">
              <Stat label="Ingestions" value={dq.total_ingestions} />
              <Stat
                label="Success rate"
                value={dq.success_rate === null ? "—" : `${(dq.success_rate * 100).toFixed(0)}%`}
              />
              <Stat label="Quarantined" value={dq.quarantined} tone={dq.quarantined ? "warn" : undefined} />
            </div>
            <div>
              <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Last updated per source
              </h4>
              {Object.keys(dq.by_source).length === 0 ? (
                <p className="text-sm text-slate-500">No ingestions yet.</p>
              ) : (
                <ul className="divide-y divide-slate-800 rounded-lg border border-slate-800 bg-slate-800/50">
                  {Object.entries(dq.by_source).map(([src, info]) => (
                    <li key={src} className="flex justify-between px-3 py-2.5 text-sm">
                      <span className="text-slate-300">{src}</span>
                      <span className="text-slate-500">
                        {new Date(info.last_updated).toLocaleString()} · {info.count}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
        {!dq && !err && <p className="text-sm text-slate-500">Loading…</p>}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string | number;
  tone?: "warn";
}) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-800/50 p-3 text-center">
      <div className={`text-2xl font-semibold ${tone === "warn" ? "text-red-400" : "text-slate-100"}`}>
        {value}
      </div>
      <div className="mt-0.5 text-[11px] uppercase tracking-wide text-slate-500">{label}</div>
    </div>
  );
}
