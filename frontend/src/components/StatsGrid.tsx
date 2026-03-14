"use client";

import { AnalyzeResponse } from "@/types";

interface Props {
  analysis: AnalyzeResponse["analysis"];
}

function fmt(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(0)}`;
}

export default function StatsGrid({ analysis }: Props) {
  const tradesDisplay = analysis.trades_capped
    ? `>${analysis.total_trades.toLocaleString()}`
    : analysis.total_trades.toLocaleString();
  const tradesPerDaySub = analysis.trades_capped
    ? "more trades exist"
    : `${analysis.timing.avg_trades_per_day.toFixed(1)}/day`;

  const stats = [
    { label: "Total Trades", value: tradesDisplay, sub: tradesPerDaySub },
    { label: "Volume", value: fmt(analysis.total_volume_usdc), sub: `avg ${fmt(analysis.sizing.avg_trade_size_usdc)}/trade` },
    { label: "Markets", value: analysis.unique_markets.toLocaleString(), sub: `${analysis.avg_trades_per_market.toFixed(1)} trades/mkt` },
    { label: "Buy/Sell", value: analysis.buy_sell_ratio.toFixed(2), sub: analysis.buy_sell_ratio > 1.5 ? "buy heavy" : "balanced" },
    { label: "Streak", value: `${analysis.timing.trading_streak_days}d`, sub: `busiest: ${analysis.timing.busiest_date_count} trades` },
    { label: "Concentration", value: (analysis.market_concentration * 100).toFixed(1) + "%", sub: analysis.market_concentration < 0.05 ? "diversified" : "concentrated" },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
      {stats.map((s, i) => (
        <div key={s.label}
          className="card-glow p-4 animate-fade-up"
          style={{ animationDelay: `${0.1 + i * 0.04}s` }}>
          <p className="text-xs uppercase tracking-widest mb-2" style={{ color: "var(--text-muted)" }}>
            {s.label}
          </p>
          <p className="stat-value text-xl mb-1">{s.value}</p>
          <p className="text-xs" style={{ color: "var(--text-secondary)", fontFamily: "'JetBrains Mono', monospace" }}>
            {s.sub}
          </p>
        </div>
      ))}
    </div>
  );
}
