export type SignalKind = "BUY" | "SELL" | "HOLD";

export interface Driver {
  feature: string;
  label: string;
  direction: "Positive" | "Negative" | "Neutral";
  contribution: number;
}

export interface SignalRow {
  ticker: string;
  sector: string;
  portfolio_id: number;
  portfolio_name: string;
  weight_pct: number;
  ret_1m_pct: number | null;
  alpha_pct: number | null;
  confidence: number;
  signal: SignalKind;
  raw_signal: SignalKind;
  breach_min: boolean;
  breach_max: boolean;
  as_of_date: string | null;
  drivers: Driver[];
  explanation: string;
  rule_notes: string[];
  quantity: number;
  wac: number;
  current_price: number | null;
  unrealised_pnl_pct: number | null;
  holding_days: number;
  derisked: boolean;
  signal_trace: SignalKind[];
}

export interface Portfolio {
  id: number;
  name: string;
  benchmark_symbol: string;
  holdings_count: number;
}

export interface Rule {
  portfolio_id: number;
  min_weight_pct: number;
  max_weight_pct: number;
  momentum_threshold_pct: number;
  volatility_ceiling: number;
  confidence_floor: number;
  derisk_override: boolean;
}

export interface DataQuality {
  total_ingestions: number;
  success: number;
  quarantined: number;
  success_rate: number | null;
  by_source: Record<string, { last_updated: string; count: number }>;
}
