import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Rule } from "../api/types";

const FIELDS: { key: keyof Omit<Rule, "portfolio_id" | "derisk_override">; label: string; step: number; suffix: string }[] = [
  { key: "min_weight_pct", label: "Min weight (buy ceiling)", step: 0.5, suffix: "%" },
  { key: "max_weight_pct", label: "Max weight (sell review)", step: 0.5, suffix: "%" },
  { key: "momentum_threshold_pct", label: "Momentum threshold", step: 0.5, suffix: "%" },
  { key: "volatility_ceiling", label: "Volatility ceiling", step: 0.1, suffix: "x" },
  { key: "confidence_floor", label: "Confidence floor", step: 1, suffix: "%" },
];

export function RulesPanel({
  portfolioId,
  onClose,
  onSaved,
}: {
  portfolioId: number;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [rule, setRule] = useState<Rule | null>(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    api.rules(portfolioId).then(setRule);
  }, [portfolioId]);

  async function save() {
    if (!rule) return;
    setSaving(true);
    setMsg(null);
    try {
      await api.updateRules(portfolioId, rule);
      await api.triggerScore();
      setMsg("Saved & re-scored. Signals updated.");
      onSaved();
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-20 flex justify-end bg-black/60" onClick={onClose}>
      <div
        className="h-full w-full max-w-sm overflow-y-auto border-l border-slate-800 bg-slate-900 p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-100">Rules & Guardrails</h3>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300">
            ✕
          </button>
        </div>
        {!rule ? (
          <p className="text-slate-500">Loading…</p>
        ) : (
          <div className="space-y-4">
            {FIELDS.map((f) => (
              <label key={f.key} className="block">
                <span className="text-sm font-medium text-slate-300">{f.label}</span>
                <div className="mt-1 flex items-center gap-2">
                  <input
                    type="number"
                    step={f.step}
                    value={rule[f.key]}
                    onChange={(e) =>
                      setRule({ ...rule, [f.key]: parseFloat(e.target.value) })
                    }
                    className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 focus:border-indigo-500 focus:outline-none"
                  />
                  <span className="w-4 shrink-0 text-sm text-slate-500">{f.suffix}</span>
                </div>
              </label>
            ))}
            <label className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-300">De-risk override</span>
              <input
                type="checkbox"
                checked={rule.derisk_override}
                onChange={(e) =>
                  setRule({ ...rule, derisk_override: e.target.checked })
                }
                className="h-4 w-4 accent-indigo-500"
              />
            </label>

            <button
              onClick={save}
              disabled={saving}
              className="w-full rounded-md bg-indigo-600 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {saving ? "Saving & re-scoring…" : "Save & re-score"}
            </button>
            {msg && <p className="text-center text-sm text-green-400">{msg}</p>}
            <p className="text-xs text-slate-600">
              Changes take effect on the next scoring run — no deployment needed.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
