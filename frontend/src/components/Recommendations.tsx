"use client";

interface Props {
  items: string[];
}

export default function Recommendations({ items }: Props) {
  return (
    <div className="card-glow p-5 mb-6 animate-fade-up" style={{ animationDelay: "0.65s" }}>
      <div className="flex items-center gap-3 mb-4">
        <div className="w-5 h-5 rounded-md flex items-center justify-center"
          style={{ background: "rgba(59,130,246,0.15)" }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
          </svg>
        </div>
        <h2 className="text-sm font-semibold uppercase tracking-widest" style={{ color: "var(--text-secondary)" }}>
          Recommendations
        </h2>
      </div>
      <div className="flex flex-col gap-3">
        {items.map((item, i) => (
          <div key={i} className="flex gap-3 p-3 rounded-lg"
            style={{ background: "rgba(59,130,246,0.03)", border: "1px solid rgba(59,130,246,0.08)" }}>
            <span className="text-xs font-mono mt-0.5 flex-shrink-0" style={{
              color: "var(--accent-blue)",
              fontFamily: "'JetBrains Mono', monospace",
            }}>
              {String(i + 1).padStart(2, "0")}
            </span>
            <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
              {item}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
