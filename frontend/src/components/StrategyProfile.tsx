"use client";

import { StrategyProfileData } from "@/types";

interface Props {
  strategy: StrategyProfileData;
}

function formatHoldTime(hours: number): string {
  if (hours < 1) return `${Math.round(hours * 60)}m`;
  if (hours < 24) return `${hours.toFixed(1)}h`;
  if (hours < 168) return `${(hours / 24).toFixed(1)}d`;
  return `${(hours / 168).toFixed(1)}w`;
}

function PnlValue({ value }: { value: number }) {
  const isPositive = value >= 0;
  return (
    <span style={{
      color: isPositive ? "var(--accent-green)" : "var(--accent-red)",
      fontFamily: "'JetBrains Mono', monospace",
    }}>
      {isPositive ? "+" : ""}${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}
    </span>
  );
}

function BoolBadge({ value, labelTrue, labelFalse }: { value: boolean; labelTrue: string; labelFalse: string }) {
  return (
    <span className="text-xs px-2 py-0.5 rounded-full" style={{
      background: value ? "rgba(16,185,129,0.1)" : "rgba(122,139,168,0.1)",
      color: value ? "var(--accent-green)" : "var(--text-muted)",
      border: `1px solid ${value ? "rgba(16,185,129,0.2)" : "rgba(122,139,168,0.15)"}`,
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: "10px",
    }}>
      {value ? labelTrue : labelFalse}
    </span>
  );
}

export default function StrategyProfile({ strategy }: Props) {
  const confidencePct = Math.round(strategy.confidence * 100);

  // Strategy type color mapping
  const strategyColors: Record<string, string> = {
    "Contrarian Value": "#10b981",
    "Momentum": "#3b82f6",
    "Scalper": "#f59e0b",
    "Event-Driven": "#8b5cf6",
    "Market Maker": "#06b6d4",
  };
  const strategyColor = strategyColors[strategy.strategy_type] || "var(--accent-blue)";

  return (
    <div className="mb-6 animate-fade-up" style={{ animationDelay: "0.25s" }}>
      {/* Strategy Type Badge + Summary */}
      <div className="card-glow p-5 mb-4">
        <div className="flex items-start gap-4 flex-wrap">
          {/* Large badge */}
          <div className="flex flex-col items-center gap-1.5 flex-shrink-0">
            <div className="px-5 py-3 rounded-lg text-center" style={{
              background: `${strategyColor}15`,
              border: `1.5px solid ${strategyColor}40`,
            }}>
              <p className="text-xs font-semibold uppercase tracking-widest mb-0.5" style={{
                color: strategyColor,
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: "10px",
              }}>
                Strategy Type
              </p>
              <p className="text-lg font-bold tracking-tight" style={{ color: strategyColor }}>
                {strategy.strategy_type}
              </p>
            </div>
            <span className="text-xs px-2 py-0.5 rounded-full" style={{
              background: confidencePct > 60 ? "rgba(16,185,129,0.1)" : "rgba(245,158,11,0.1)",
              color: confidencePct > 60 ? "var(--accent-green)" : "var(--accent-amber)",
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: "10px",
              border: `1px solid ${confidencePct > 60 ? "rgba(16,185,129,0.2)" : "rgba(245,158,11,0.2)"}`,
            }}>
              {confidencePct}% confidence
            </span>
          </div>

          {/* Summary text */}
          <div className="flex-1 min-w-[200px]">
            <h2 className="text-sm font-semibold uppercase tracking-widest mb-2" style={{ color: "var(--text-secondary)" }}>
              Strategy Summary
            </h2>
            <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
              {strategy.summary}
            </p>

            {/* Quick stats row */}
            <div className="flex flex-wrap gap-3 mt-3">
              <span className="text-xs px-2 py-1 rounded" style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                color: "var(--text-secondary)",
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: "10px",
              }}>
                Avg Entry: ${strategy.avg_entry_price.toFixed(2)}
              </span>
              <span className="text-xs px-2 py-1 rounded" style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                color: "var(--text-secondary)",
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: "10px",
              }}>
                Hold Time: {formatHoldTime(strategy.avg_time_in_market)}
              </span>
              <span className="text-xs px-2 py-1 rounded" style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                color: "var(--text-secondary)",
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: "10px",
              }}>
                Trades/Market: {strategy.avg_trades_per_market.toFixed(1)}
              </span>
              <span className="text-xs px-2 py-1 rounded" style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                color: "var(--text-secondary)",
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: "10px",
              }}>
                Timing: {strategy.market_entry_timing}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Key Edges & Weaknesses Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        {/* Key Edges */}
        <div className="card-glow p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-1.5 h-5 rounded-full" style={{ background: "var(--accent-green)" }} />
            <h3 className="text-sm font-semibold uppercase tracking-widest" style={{ color: "var(--text-secondary)" }}>
              Key Edges
            </h3>
          </div>
          <div className="flex flex-col gap-2">
            {strategy.key_edges.map((edge, i) => (
              <div key={i} className="flex gap-2 p-2.5 rounded-lg" style={{
                background: "rgba(16,185,129,0.03)",
                border: "1px solid rgba(16,185,129,0.08)",
              }}>
                <span className="text-xs mt-0.5 flex-shrink-0" style={{
                  color: "var(--accent-green)",
                  fontFamily: "'JetBrains Mono', monospace",
                }}>+</span>
                <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>{edge}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Weaknesses */}
        <div className="card-glow p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-1.5 h-5 rounded-full" style={{ background: "var(--accent-red)" }} />
            <h3 className="text-sm font-semibold uppercase tracking-widest" style={{ color: "var(--text-secondary)" }}>
              Weaknesses
            </h3>
          </div>
          <div className="flex flex-col gap-2">
            {strategy.weaknesses.map((w, i) => (
              <div key={i} className="flex gap-2 p-2.5 rounded-lg" style={{
                background: "rgba(239,68,68,0.03)",
                border: "1px solid rgba(239,68,68,0.08)",
              }}>
                <span className="text-xs mt-0.5 flex-shrink-0" style={{
                  color: "var(--accent-red)",
                  fontFamily: "'JetBrains Mono', monospace",
                }}>-</span>
                <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>{w}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Edge by Category & Price Range */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        {/* Edge by Category */}
        <div className="card-glow p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-1.5 h-5 rounded-full" style={{ background: "var(--gradient-primary)" }} />
            <h3 className="text-sm font-semibold uppercase tracking-widest" style={{ color: "var(--text-secondary)" }}>
              Edge by Category
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
              <thead>
                <tr style={{ color: "var(--text-muted)" }}>
                  <th className="text-left py-2 pr-3 font-medium">Category</th>
                  <th className="text-right py-2 px-3 font-medium">Trades</th>
                  <th className="text-right py-2 px-3 font-medium">Win Rate</th>
                  <th className="text-right py-2 pl-3 font-medium">PnL</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(strategy.edge_by_category)
                  .sort(([, a], [, b]) => b.pnl - a.pnl)
                  .map(([cat, stats]) => {
                    const isBest = cat === strategy.best_category;
                    const isWorst = cat === strategy.worst_category;
                    return (
                      <tr key={cat} className="transition-colors" style={{
                        borderTop: "1px solid var(--border)",
                      }}>
                        <td className="py-2 pr-3" style={{ color: "var(--text-primary)" }}>
                          <span className="flex items-center gap-1.5">
                            {cat}
                            {isBest && (
                              <span className="text-[9px] px-1.5 py-0.5 rounded-full" style={{
                                background: "rgba(16,185,129,0.1)", color: "var(--accent-green)",
                              }}>BEST</span>
                            )}
                            {isWorst && (
                              <span className="text-[9px] px-1.5 py-0.5 rounded-full" style={{
                                background: "rgba(239,68,68,0.1)", color: "var(--accent-red)",
                              }}>WORST</span>
                            )}
                          </span>
                        </td>
                        <td className="text-right py-2 px-3" style={{ color: "var(--text-secondary)" }}>
                          {stats.trades}
                        </td>
                        <td className="text-right py-2 px-3" style={{
                          color: stats.win_rate > 50 ? "var(--accent-green)" : stats.win_rate < 40 ? "var(--accent-red)" : "var(--text-secondary)",
                        }}>
                          {stats.win_rate.toFixed(0)}%
                        </td>
                        <td className="text-right py-2 pl-3">
                          <PnlValue value={stats.pnl} />
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Edge by Price Range */}
        <div className="card-glow p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-1.5 h-5 rounded-full" style={{ background: "var(--gradient-primary)" }} />
            <h3 className="text-sm font-semibold uppercase tracking-widest" style={{ color: "var(--text-secondary)" }}>
              Edge by Price Range
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
              <thead>
                <tr style={{ color: "var(--text-muted)" }}>
                  <th className="text-left py-2 pr-3 font-medium">Range</th>
                  <th className="text-right py-2 px-3 font-medium">Trades</th>
                  <th className="text-right py-2 px-3 font-medium">Win Rate</th>
                  <th className="text-right py-2 pl-3 font-medium">PnL</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(strategy.edge_by_price_range).map(([range, stats]) => (
                  <tr key={range} style={{ borderTop: "1px solid var(--border)" }}>
                    <td className="py-2 pr-3" style={{ color: "var(--text-primary)" }}>${range}</td>
                    <td className="text-right py-2 px-3" style={{ color: "var(--text-secondary)" }}>{stats.trades}</td>
                    <td className="text-right py-2 px-3" style={{
                      color: stats.win_rate > 50 ? "var(--accent-green)" : stats.win_rate < 40 ? "var(--accent-red)" : "var(--text-secondary)",
                    }}>
                      {stats.trades > 0 ? `${stats.win_rate.toFixed(0)}%` : "-"}
                    </td>
                    <td className="text-right py-2 pl-3">
                      {stats.trades > 0 ? <PnlValue value={stats.pnl} /> : <span style={{ color: "var(--text-muted)" }}>-</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Position Management */}
      <div className="card-glow p-5 mb-4">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-1.5 h-5 rounded-full" style={{ background: "var(--gradient-primary)" }} />
          <h3 className="text-sm font-semibold uppercase tracking-widest" style={{ color: "var(--text-secondary)" }}>
            Position Management
          </h3>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="text-center p-3 rounded-lg" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <p className="text-xs mb-1.5" style={{ color: "var(--text-muted)" }}>Scales In</p>
            <BoolBadge value={strategy.scales_in} labelTrue="YES" labelFalse="NO" />
          </div>
          <div className="text-center p-3 rounded-lg" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <p className="text-xs mb-1.5" style={{ color: "var(--text-muted)" }}>Scales Out</p>
            <BoolBadge value={strategy.scales_out} labelTrue="YES" labelFalse="NO" />
          </div>
          <div className="text-center p-3 rounded-lg" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <p className="text-xs mb-1.5" style={{ color: "var(--text-muted)" }}>Both Sides</p>
            <BoolBadge value={strategy.uses_both_sides} labelTrue="YES" labelFalse="NO" />
          </div>
          <div className="text-center p-3 rounded-lg" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <p className="text-xs mb-1.5" style={{ color: "var(--text-muted)" }}>Hold Style</p>
            <span className="text-xs px-2 py-0.5 rounded-full" style={{
              background: strategy.quick_flipper ? "rgba(245,158,11,0.1)" : strategy.long_holder ? "rgba(59,130,246,0.1)" : "rgba(122,139,168,0.1)",
              color: strategy.quick_flipper ? "var(--accent-amber)" : strategy.long_holder ? "var(--accent-blue)" : "var(--text-muted)",
              border: `1px solid ${strategy.quick_flipper ? "rgba(245,158,11,0.2)" : strategy.long_holder ? "rgba(59,130,246,0.2)" : "rgba(122,139,168,0.15)"}`,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: "10px",
            }}>
              {strategy.quick_flipper ? "QUICK FLIP" : strategy.long_holder ? "LONG HOLD" : "MEDIUM"}
            </span>
          </div>
          <div className="text-center p-3 rounded-lg" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <p className="text-xs mb-1.5" style={{ color: "var(--text-muted)" }}>Prefers</p>
            <span className="text-xs px-2 py-0.5 rounded-full" style={{
              background: strategy.prefers_underdogs ? "rgba(139,92,246,0.1)" : strategy.prefers_favorites ? "rgba(59,130,246,0.1)" : "rgba(122,139,168,0.1)",
              color: strategy.prefers_underdogs ? "#8b5cf6" : strategy.prefers_favorites ? "var(--accent-blue)" : "var(--text-muted)",
              border: `1px solid ${strategy.prefers_underdogs ? "rgba(139,92,246,0.2)" : strategy.prefers_favorites ? "rgba(59,130,246,0.2)" : "rgba(122,139,168,0.15)"}`,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: "10px",
            }}>
              {strategy.prefers_underdogs ? "UNDERDOGS" : strategy.prefers_favorites ? "FAVORITES" : "BALANCED"}
            </span>
          </div>
          <div className="text-center p-3 rounded-lg" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <p className="text-xs mb-1.5" style={{ color: "var(--text-muted)" }}>Avg Hold</p>
            <span className="text-sm font-semibold" style={{
              color: "var(--text-primary)",
              fontFamily: "'JetBrains Mono', monospace",
            }}>
              {formatHoldTime(strategy.avg_time_in_market)}
            </span>
          </div>
        </div>
      </div>

      {/* Replication Tips */}
      <div className="card-glow p-5">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-5 h-5 rounded-md flex items-center justify-center" style={{ background: "rgba(139,92,246,0.15)" }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
          </div>
          <h3 className="text-sm font-semibold uppercase tracking-widest" style={{ color: "var(--text-secondary)" }}>
            How to Replicate This Strategy
          </h3>
        </div>
        <div className="flex flex-col gap-2">
          {strategy.replication_tips.map((tip, i) => (
            <div key={i} className="flex gap-3 p-3 rounded-lg" style={{
              background: "rgba(139,92,246,0.03)",
              border: "1px solid rgba(139,92,246,0.08)",
            }}>
              <span className="text-xs font-mono mt-0.5 flex-shrink-0" style={{
                color: "#8b5cf6",
                fontFamily: "'JetBrains Mono', monospace",
              }}>
                {String(i + 1).padStart(2, "0")}
              </span>
              <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                {tip}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
