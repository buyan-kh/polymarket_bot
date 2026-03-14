"use client";

import { ProCon } from "@/types";

interface Props {
  pros: ProCon[];
  cons: ProCon[];
}

export default function StrengthsWeaknesses({ pros, cons }: Props) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
      {/* Strengths */}
      <div className="card-glow p-5 animate-fade-up" style={{ animationDelay: "0.5s" }}>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-5 h-5 rounded-md flex items-center justify-center text-xs"
            style={{ background: "rgba(16,185,129,0.15)", color: "var(--accent-green)" }}>
            +
          </div>
          <h2 className="text-sm font-semibold uppercase tracking-widest" style={{ color: "var(--text-secondary)" }}>
            Strengths
          </h2>
          <span className="ml-auto text-xs px-2 py-0.5 rounded-full"
            style={{
              background: "rgba(16,185,129,0.1)",
              color: "var(--accent-green)",
              fontFamily: "'JetBrains Mono', monospace",
            }}>
            {pros.length}
          </span>
        </div>
        <div className="flex flex-col gap-3">
          {pros.map((p, i) => (
            <div key={i} className="p-3 rounded-lg transition-colors"
              style={{ background: "rgba(16,185,129,0.03)", border: "1px solid rgba(16,185,129,0.08)" }}>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs px-2 py-0.5 rounded-full"
                  style={{
                    background: "rgba(16,185,129,0.1)",
                    color: "var(--accent-green)",
                    fontSize: "10px",
                    fontFamily: "'JetBrains Mono', monospace",
                  }}>
                  {p.category}
                </span>
                <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                  {p.observation}
                </span>
              </div>
              <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                {p.detail}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Weaknesses */}
      <div className="card-glow p-5 animate-fade-up" style={{ animationDelay: "0.55s" }}>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-5 h-5 rounded-md flex items-center justify-center text-xs"
            style={{ background: "rgba(239,68,68,0.15)", color: "var(--accent-red)" }}>
            !
          </div>
          <h2 className="text-sm font-semibold uppercase tracking-widest" style={{ color: "var(--text-secondary)" }}>
            Weaknesses
          </h2>
          <span className="ml-auto text-xs px-2 py-0.5 rounded-full"
            style={{
              background: "rgba(239,68,68,0.1)",
              color: "var(--accent-red)",
              fontFamily: "'JetBrains Mono', monospace",
            }}>
            {cons.length}
          </span>
        </div>
        <div className="flex flex-col gap-3">
          {cons.map((c, i) => {
            const severityClass = `severity-${c.severity}`;
            return (
              <div key={i} className="p-3 rounded-lg transition-colors"
                style={{ background: "rgba(239,68,68,0.02)", border: "1px solid rgba(239,68,68,0.06)" }}>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${severityClass}`}
                    style={{ fontSize: "10px", fontFamily: "'JetBrains Mono', monospace" }}>
                    {c.severity}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-full"
                    style={{
                      background: "rgba(122,139,168,0.1)",
                      color: "var(--text-muted)",
                      fontSize: "10px",
                      fontFamily: "'JetBrains Mono', monospace",
                    }}>
                    {c.category}
                  </span>
                  <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                    {c.observation}
                  </span>
                </div>
                <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                  {c.detail}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
