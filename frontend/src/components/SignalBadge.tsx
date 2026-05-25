import type { SignalKind } from "../api/types";

const STYLES: Record<SignalKind, string> = {
  BUY: "bg-green-100 text-green-800 ring-green-600/30",
  SELL: "bg-red-100 text-red-800 ring-red-600/30",
  HOLD: "bg-amber-100 text-amber-800 ring-amber-600/30",
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
