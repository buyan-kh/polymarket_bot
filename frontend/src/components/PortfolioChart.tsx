"use client";

import { PortfolioSnapshot } from "@/types";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

interface Props {
  snapshots: PortfolioSnapshot[];
}

export default function PortfolioChart({ snapshots }: Props) {
  const chartData = snapshots.map((s) => ({
    trade: s.trade_count,
    value: Math.round(s.total_value),
    cash: Math.round(s.cash),
    positions: Math.round(s.positions_value),
  }));

  return (
    <div className="card-glow p-5 animate-fade-up" style={{ animationDelay: "0.3s" }}>
      <div className="flex items-center gap-3 mb-4">
        <div className="w-1.5 h-5 rounded-full" style={{ background: "var(--accent-blue)" }} />
        <h2 className="text-sm font-semibold uppercase tracking-widest" style={{ color: "var(--text-secondary)" }}>
          Backtest (Simulated)
        </h2>
      </div>
      <div className="h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <defs>
              <linearGradient id="gradValue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="trade"
              tickFormatter={(v) => `${v}`}
              tick={{ fontSize: 11 }}
            />
            <YAxis
              tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
              tick={{ fontSize: 11 }}
              width={55}
            />
            <Tooltip
              contentStyle={{
                background: "#0f1420",
                border: "1px solid #1a2236",
                borderRadius: "8px",
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: "12px",
                color: "#e8ecf4",
              }}
              formatter={(val) => [`$${Number(val).toLocaleString()}`, "Value"]}
              labelFormatter={(l) => `Trade #${l}`}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="#3b82f6"
              strokeWidth={2}
              fill="url(#gradValue)"
              dot={false}
              activeDot={{ r: 4, fill: "#3b82f6" }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
