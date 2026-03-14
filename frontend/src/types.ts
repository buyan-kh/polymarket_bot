export interface AnalyzeResponse {
  profile: {
    username: string;
    wallet: string;
  };
  analysis: {
    total_trades: number;
    trades_capped: boolean;
    total_volume_usdc: number;
    unique_markets: number;
    date_range: [string, string];
    buy_sell_ratio: number;
    market_concentration: number;
    avg_trades_per_market: number;
    timing: {
      most_active_hours: [number, number][];
      most_active_days: [string, number][];
      avg_trades_per_day: number;
      busiest_date: string;
      busiest_date_count: number;
      trading_streak_days: number;
    };
    sizing: {
      avg_trade_size_usdc: number;
      median_trade_size_usdc: number;
      max_trade_size_usdc: number;
      min_trade_size_usdc: number;
      stddev_trade_size: number;
      size_buckets: Record<string, number>;
    };
    pricing: {
      avg_buy_price: number;
      median_buy_price: number;
      pct_buying_below_50c: number;
      pct_buying_above_50c: number;
      avg_sell_price: number;
      favorite_price_ranges: [string, number][];
    };
    category_breakdown: Record<string, number>;
    outcome_preference: Record<string, number>;
    top_markets_by_volume: [string, number][];
    top_markets_by_trades: [string, number][];
    market_summaries: MarketSummary[];
  };
  backtest: BacktestData | null;
  baseline: BaselineData | null;
  report: ReportData;
  strategy: StrategyProfileData;
}

export interface MarketSummary {
  title: string;
  slug: string;
  total_trades: number;
  buy_count: number;
  sell_count: number;
  total_volume: number;
  avg_buy_price: number;
  avg_sell_price: number;
  estimated_pnl: number;
  outcomes_traded: string[];
}

export interface BacktestData {
  initial_capital: number;
  final_value: number;
  total_return_pct: number;
  total_pnl: number;
  max_drawdown_pct: number;
  peak_value: number;
  num_trades: number;
  num_winning_trades: number;
  num_losing_trades: number;
  win_rate: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  avg_trade_pnl: number;
  largest_win: number;
  largest_loss: number;
  snapshots: PortfolioSnapshot[];
  daily_returns: number[];
}

export interface PortfolioSnapshot {
  timestamp: string;
  cash: number;
  positions_value: number;
  total_value: number;
  trade_count: number;
}

export interface BaselineData {
  user_total_pnl: number;
  user_return_pct: number;
  inverse_estimated_pnl: number;
  random_baseline_pnl: number;
  beats_random: boolean;
  edge_vs_random: number;
}

export interface ReportData {
  summary: string;
  pros: ProCon[];
  cons: ProCon[];
  key_stats: Record<string, string | number>;
  recommendations: string[];
}

export interface ProCon {
  category: string;
  observation: string;
  detail: string;
  severity: "info" | "warning" | "critical";
}

export interface EdgeStats {
  trades: number;
  pnl: number;
  win_rate: number;
}

export interface StrategyProfileData {
  strategy_type: string;
  confidence: number;
  avg_entry_price: number;
  entry_price_distribution: Record<string, number>;
  prefers_underdogs: boolean;
  prefers_favorites: boolean;
  avg_time_in_market: number;
  quick_flipper: boolean;
  long_holder: boolean;
  edge_by_category: Record<string, EdgeStats>;
  edge_by_price_range: Record<string, EdgeStats>;
  best_category: string;
  worst_category: string;
  market_entry_timing: string;
  avg_market_age_at_entry: number;
  scales_in: boolean;
  scales_out: boolean;
  avg_trades_per_market: number;
  uses_both_sides: boolean;
  profitable_patterns: string[];
  unprofitable_patterns: string[];
  summary: string;
  key_edges: string[];
  weaknesses: string[];
  replication_tips: string[];
}

export interface ProfileHistoryEntry {
  id: number;
  username: string;
  wallet: string;
  total_trades: number;
  total_volume: number;
  total_return_pct: number | null;
  win_rate: number | null;
  sharpe_ratio: number | null;
  analyzed_at: string;
  notes: string | null;
}
