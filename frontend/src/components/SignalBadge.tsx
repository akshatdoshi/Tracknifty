import type { SignalKind } from "../api/types";

const STYLES: Record<SignalKind, string> = {
  BUY: "bg-green-900/60 text-green-400 ring-green-500/30",
  SELL: "bg-red-900/60 text-red-400 ring-red-500/30",
  HOLD: "bg-amber-900/60 text-amber-400 ring-amber-500/30",
};

export function SignalBadge({ signal, small }: { signal: SignalKind; small?: boolean }) {
  return (
    <span
      className={`inline-flex items-center rounded-full font-semibold ring-1 ring-inset ${
        small ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs"
      } ${STYLES[signal]}`}
    >
      {signal}
    </span>
  );
}
