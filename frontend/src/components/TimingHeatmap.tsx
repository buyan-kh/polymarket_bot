"use client";

interface Props {
  hours: [number, number][];
  days: [string, number][];
}

export default function TimingHeatmap({ hours, days }: Props) {
  // Build a full 24-hour view
  const hourMap = new Map(hours);
  const maxHour = Math.max(...hours.map(([, c]) => c), 1);
  const allHours = Array.from({ length: 24 }, (_, i) => ({
    hour: i,
    count: hourMap.get(i) || 0,
  }));

  const dayOrder = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
  const dayMap = new Map(days);
  const maxDay = Math.max(...days.map(([, c]) => c), 1);
  const allDays = dayOrder.map((d) => ({
    day: d,
    short: d.slice(0, 3),
    count: dayMap.get(d) || 0,
  }));

  return (
    <div className="card-glow p-5 animate-fade-up" style={{ animationDelay: "0.4s" }}>
      <div className="flex items-center gap-3 mb-4">
        <div className="w-1.5 h-5 rounded-full" style={{ background: "var(--accent-cyan)" }} />
        <h2 className="text-sm font-semibold uppercase tracking-widest" style={{ color: "var(--text-secondary)" }}>
          Trading Activity
        </h2>
      </div>

      {/* Hour bars */}
      <p className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>By Hour (UTC)</p>
      <div className="flex items-end gap-[3px] h-[100px] mb-6">
        {allHours.map(({ hour, count }) => {
          const pct = count / maxHour;
          return (
            <div key={hour} className="flex-1 flex flex-col items-center gap-1 group relative">
              <div
                className="w-full rounded-sm transition-all duration-200 group-hover:brightness-125"
                style={{
                  height: `${Math.max(pct * 100, 2)}%`,
                  background: pct > 0.7
                    ? "var(--accent-blue)"
                    : pct > 0.3
                    ? "rgba(59,130,246,0.5)"
                    : "rgba(59,130,246,0.15)",
                  minHeight: "2px",
                }}
              />
              {hour % 4 === 0 && (
                <span className="text-[9px]" style={{
                  color: "var(--text-muted)",
                  fontFamily: "'JetBrains Mono', monospace",
                }}>
                  {hour}
                </span>
              )}
              {/* Tooltip */}
              <div className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 rounded text-[10px] opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10"
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  color: "var(--text-primary)",
                  fontFamily: "'JetBrains Mono', monospace",
                }}>
                {hour}:00 &mdash; {count.toLocaleString()}
              </div>
            </div>
          );
        })}
      </div>

      {/* Day bars */}
      <p className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>By Day</p>
      <div className="flex flex-col gap-2">
        {allDays.map(({ day, short, count }) => {
          const pct = count / maxDay;
          return (
            <div key={day} className="flex items-center gap-3">
              <span className="w-8 text-xs text-right" style={{
                color: "var(--text-muted)",
                fontFamily: "'JetBrains Mono', monospace",
              }}>
                {short}
              </span>
              <div className="flex-1 h-4 rounded-sm overflow-hidden" style={{ background: "rgba(59,130,246,0.08)" }}>
                <div
                  className="h-full rounded-sm transition-all duration-500"
                  style={{
                    width: `${Math.max(pct * 100, 1)}%`,
                    background: pct > 0.7 ? "var(--accent-blue)" : "rgba(59,130,246,0.5)",
                  }}
                />
              </div>
              <span className="w-12 text-xs text-right tabular-nums" style={{
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
