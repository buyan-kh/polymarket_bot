"use client";

import { MarketSummary } from "@/types";

interface Props {
  markets: MarketSummary[];
}

export default function TopMarkets({ markets }: Props) {
  return (
    <div className="card-glow p-5 mb-6 animate-fade-up" style={{ animationDelay: "0.6s" }}>
      <div className="flex items-center gap-3 mb-4">
        <div className="w-1.5 h-5 rounded-full" style={{ background: "var(--accent-amber)" }} />
        <h2 className="text-sm font-semibold uppercase tracking-widest" style={{ color: "var(--text-secondary)" }}>
          Top Markets
        </h2>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
          <thead>
            <tr style={{ color: "var(--text-muted)" }}>
              <th className="text-left py-2 pr-4 text-xs font-normal">#</th>
              <th className="text-left py-2 pr-4 text-xs font-normal">Market</th>
              <th className="text-right py-2 px-3 text-xs font-normal">Volume</th>
              <th className="text-right py-2 px-3 text-xs font-normal">Trades</th>
              <th className="text-right py-2 px-3 text-xs font-normal">Buys</th>
              <th className="text-right py-2 px-3 text-xs font-normal">Sells</th>
              <th className="text-right py-2 pl-3 text-xs font-normal">Est. PnL</th>
            </tr>
          </thead>
          <tbody>
            {markets.slice(0, 15).map((m, i) => {
              const pnlColor = m.estimated_pnl >= 0 ? "var(--accent-green)" : "var(--accent-red)";
              return (
                <tr key={i} className="transition-colors"
                  style={{ borderTop: "1px solid var(--border)" }}>
                  <td className="py-2.5 pr-4 text-xs" style={{ color: "var(--text-muted)" }}>
                    {i + 1}
                  </td>
                  <td className="py-2.5 pr-4 max-w-[300px] truncate text-xs" style={{ color: "var(--text-primary)" }}>
                    {m.title || m.slug || "Unknown"}
                  </td>
                  <td className="py-2.5 px-3 text-right text-xs" style={{ color: "var(--text-secondary)" }}>
                    ${m.total_volume.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </td>
                  <td className="py-2.5 px-3 text-right text-xs" style={{ color: "var(--text-secondary)" }}>
                    {m.total_trades.toLocaleString()}
                  </td>
                  <td className="py-2.5 px-3 text-right text-xs" style={{ color: "rgba(59,130,246,0.7)" }}>
                    {m.buy_count}
                  </td>
                  <td className="py-2.5 px-3 text-right text-xs" style={{ color: "rgba(239,68,68,0.7)" }}>
                    {m.sell_count}
                  </td>
                  <td className="py-2.5 pl-3 text-right text-xs font-medium" style={{ color: pnlColor }}>
                    {m.estimated_pnl >= 0 ? "+" : ""}${m.estimated_pnl.toFixed(0)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
