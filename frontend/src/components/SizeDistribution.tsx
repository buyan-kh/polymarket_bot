"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

interface Props {
  buckets: Record<string, number>;
  priceRanges: [string, number][];
}

const BUCKET_COLORS = ["#06b6d4", "#3b82f6", "#8b5cf6", "#f59e0b", "#ef4444"];

export default function SizeDistribution({ buckets, priceRanges }: Props) {
  const bucketData = Object.entries(buckets).map(([name, count]) => ({
    name: name.replace("$", ""),
    count,
  }));

  const priceData = priceRanges.map(([range, count]) => ({
    range: range.replace(/\$/g, ""),
    count,
  }));

  return (
    <div className="card-glow p-5 animate-fade-up" style={{ animationDelay: "0.45s" }}>
      <div className="flex items-center gap-3 mb-4">
        <div className="w-1.5 h-5 rounded-full" style={{ background: "var(--accent-green)" }} />
        <h2 className="text-sm font-semibold uppercase tracking-widest" style={{ color: "var(--text-secondary)" }}>
          Distributions
        </h2>
      </div>

      <p className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>Trade Size</p>
      <div className="h-[120px] mb-5">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={bucketData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <XAxis dataKey="name" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip
              contentStyle={{
                background: "#0f1420",
                border: "1px solid #1a2236",
                borderRadius: "8px",
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: "12px",
                color: "#e8ecf4",
              }}
              formatter={(val) => [`${Number(val).toLocaleString()} trades`, ""]}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {bucketData.map((_, i) => (
                <Cell key={i} fill={BUCKET_COLORS[i % BUCKET_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <p className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>Buy Price (Top Ranges)</p>
      <div className="flex flex-col gap-1.5">
        {priceData.map(({ range, count }) => {
          const max = Math.max(...priceData.map((d) => d.count), 1);
          const pct = count / max;
          return (
            <div key={range} className="flex items-center gap-2">
              <span className="w-20 text-[10px] text-right" style={{
                color: "var(--text-muted)",
                fontFamily: "'JetBrains Mono', monospace",
              }}>
                {range}
              </span>
              <div className="flex-1 h-3 rounded-sm overflow-hidden" style={{ background: "rgba(139,92,246,0.08)" }}>
                <div className="h-full rounded-sm" style={{
                  width: `${pct * 100}%`,
                  background: "var(--accent-violet)",
                  opacity: 0.4 + pct * 0.6,
                }} />
              </div>
              <span className="w-10 text-[10px] text-right tabular-nums" style={{
                color: "var(--text-secondary)",
                fontFamily: "'JetBrains Mono', monospace",
              }}>
                {count.toLocaleString()}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
