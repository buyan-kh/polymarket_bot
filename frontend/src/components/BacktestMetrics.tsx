"use client";

import { BacktestData } from "@/types";

interface Props {
  backtest: BacktestData;
}

export default function BacktestMetrics({ backtest }: Props) {
  const isPositive = backtest.total_return_pct >= 0;

  const metrics = [
    {
      label: "Return",
      value: `${isPositive ? "+" : ""}${backtest.total_return_pct.toFixed(1)}%`,
      color: isPositive ? "var(--accent-green)" : "var(--accent-red)",
    },
    { label: "Sharpe", value: backtest.sharpe_ratio.toFixed(2), color: backtest.sharpe_ratio > 1 ? "var(--accent-green)" : "var(--text-primary)" },
    { label: "Sortino", value: backtest.sortino_ratio.toFixed(2), color: backtest.sortino_ratio > 1 ? "var(--accent-green)" : "var(--text-primary)" },
    { label: "Win Rate", value: `${backtest.win_rate.toFixed(1)}%`, color: backtest.win_rate > 50 ? "var(--accent-green)" : "var(--accent-red)" },
    { label: "Profit Factor", value: backtest.profit_factor.toFixed(2), color: backtest.profit_factor > 1 ? "var(--accent-green)" : "var(--accent-red)" },
    { label: "Max DD", value: `-${backtest.max_drawdown_pct.toFixed(1)}%`, color: backtest.max_drawdown_pct > 30 ? "var(--accent-red)" : "var(--accent-amber)" },
    { label: "Avg Win", value: `$${backtest.avg_win.toFixed(0)}`, color: "var(--accent-green)" },
    { label: "Avg Loss", value: `$${Math.abs(backtest.avg_loss).toFixed(0)}`, color: "var(--accent-red)" },
  ];

  return (
    <div className="card-glow p-5 mb-6 animate-fade-up" style={{ animationDelay: "0.2s" }}>
      <div className="flex items-center gap-3 mb-4">
        <div className="w-1.5 h-5 rounded-full" style={{ background: "var(--gradient-primary)" }} />
        <h2 className="text-sm font-semibold uppercase tracking-widest" style={{ color: "var(--text-secondary)" }}>
          Backtest Results
        </h2>
        <span className="ml-auto text-xs px-3 py-1 rounded-full"
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            background: isPositive ? "rgba(16,185,129,0.1)" : "rgba(239,68,68,0.1)",
            border: `1px solid ${isPositive ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)"}`,
            color: isPositive ? "var(--accent-green)" : "var(--accent-red)",
          }}>
          ${backtest.initial_capital.toLocaleString()} &rarr; ${backtest.final_value.toLocaleString()}
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
        {metrics.map((m) => (
          <div key={m.label} className="text-center">
            <p className="text-xs mb-1.5" style={{ color: "var(--text-muted)" }}>{m.label}</p>
            <p className="text-lg font-semibold" style={{
              color: m.color,
              fontFamily: "'JetBrains Mono', monospace",
            }}>
              {m.value}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
