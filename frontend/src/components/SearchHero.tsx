"use client";

import { useState, FormEvent } from "react";

interface Props {
  onSearch: (profile: string) => void;
  error: string | null;
}

export default function SearchHero({ onSearch, error }: Props) {
  const [input, setInput] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (input.trim()) onSearch(input.trim());
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-6">
      {/* Ambient glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full opacity-20 pointer-events-none"
        style={{ background: "radial-gradient(circle, rgba(59,130,246,0.3) 0%, rgba(139,92,246,0.15) 40%, transparent 70%)" }}
      />

      <div className="relative animate-fade-up" style={{ animationDelay: "0.1s" }}>
        {/* Logo mark */}
        <div className="flex items-center justify-center mb-8">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center"
            style={{ background: "var(--gradient-primary)" }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
        </div>

        <h1 className="text-5xl font-bold text-center tracking-tight mb-3"
          style={{ fontFamily: "'Outfit', sans-serif" }}>
          <span className="stat-value">Polymarket</span>{" "}
          <span style={{ color: "var(--text-primary)" }}>Analyzer</span>
        </h1>

        <p className="text-center mb-10 text-lg" style={{ color: "var(--text-secondary)" }}>
          Deep analytics for any Polymarket trading profile
        </p>
      </div>

      <form onSubmit={handleSubmit}
        className="relative w-full max-w-xl animate-fade-up"
        style={{ animationDelay: "0.25s" }}>
        <div className="relative group">
          <div className="absolute -inset-0.5 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"
            style={{ background: "var(--gradient-primary)", filter: "blur(8px)" }} />
          <div className="relative flex items-center rounded-2xl overflow-hidden"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <div className="pl-5 pr-2" style={{ color: "var(--text-muted)" }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.3-4.3" />
              </svg>
            </div>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="@username, profile URL, or 0x wallet..."
              className="flex-1 bg-transparent py-4 px-2 text-base outline-none placeholder-opacity-50"
              style={{
                color: "var(--text-primary)",
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: "14px",
              }}
              autoFocus
            />
            <button
              type="submit"
              disabled={!input.trim()}
              className="m-2 px-5 py-2.5 rounded-xl font-medium text-sm text-white transition-all duration-200 disabled:opacity-30 hover:brightness-110 active:scale-95"
              style={{
                background: "var(--gradient-primary)",
                fontFamily: "'Outfit', sans-serif",
              }}
            >
              Analyze
            </button>
          </div>
        </div>
      </form>

      {error && (
        <div className="mt-6 px-5 py-3 rounded-xl text-sm animate-fade-up max-w-xl w-full"
          style={{
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.2)",
            color: "var(--accent-red)",
            fontFamily: "'JetBrains Mono', monospace",
          }}>
          {error}
        </div>
      )}

      <div className="mt-10 flex gap-6 animate-fade-up" style={{ animationDelay: "0.4s" }}>
        {["@Sharky6999", "@PolyTrader", "0x751a..."].map((example) => (
          <button
            key={example}
            onClick={() => setInput(example)}
            className="px-4 py-2 rounded-lg text-xs transition-all hover:brightness-125"
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              color: "var(--text-muted)",
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
}
