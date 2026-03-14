"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";

interface Props {
  categories: Record<string, number>;
}

const COLORS = ["#3b82f6", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#ec4899"];

export default function CategoryChart({ categories }: Props) {
  const data = Object.entries(categories)
    .sort((a, b) => b[1] - a[1])
    .map(([name, value]) => ({ name, value }));

  const total = data.reduce((s, d) => s + d.value, 0);

  return (
    <div className="card-glow p-5 animate-fade-up" style={{ animationDelay: "0.35s" }}>
      <div className="flex items-center gap-3 mb-4">
        <div className="w-1.5 h-5 rounded-full" style={{ background: "var(--accent-violet)" }} />
        <h2 className="text-sm font-semibold uppercase tracking-widest" style={{ color: "var(--text-secondary)" }}>
          Category Breakdown
        </h2>
      </div>
      <div className="flex items-center gap-6">
        <div className="h-[240px] w-[240px] flex-shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={3}
                dataKey="value"
                stroke="none"
              >
                {data.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
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
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="flex flex-col gap-2.5 flex-1 min-w-0">
          {data.map((d, i) => (
            <div key={d.name} className="flex items-center gap-3">
              <div className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
                style={{ background: COLORS[i % COLORS.length] }} />
              <span className="text-sm truncate flex-1" style={{ color: "var(--text-secondary)" }}>
                {d.name}
              </span>
              <span className="text-xs tabular-nums" style={{
                color: "var(--text-muted)",
                fontFamily: "'JetBrains Mono', monospace",
              }}>
                {((d.value / total) * 100).toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
