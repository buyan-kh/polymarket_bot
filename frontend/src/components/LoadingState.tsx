"use client";

import { useEffect, useState } from "react";

const MESSAGES = [
  "Resolving profile...",
  "Fetching trade history...",
  "Analyzing patterns...",
  "Running backtest simulation...",
  "Generating insights...",
];

export default function LoadingState() {
  const [msgIdx, setMsgIdx] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setMsgIdx((prev) => Math.min(prev + 1, MESSAGES.length - 1));
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-6">
      {/* Animated glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] rounded-full pointer-events-none"
        style={{
          background: "radial-gradient(circle, rgba(59,130,246,0.25) 0%, rgba(139,92,246,0.1) 50%, transparent 70%)",
          animation: "pulse-glow 2s ease-in-out infinite",
        }}
      />

      <div className="relative flex flex-col items-center">
        {/* Spinning ring */}
        <div className="w-16 h-16 rounded-full mb-8"
          style={{
            border: "3px solid var(--border)",
            borderTopColor: "var(--accent-blue)",
            animation: "spin 1s linear infinite",
          }}
        />

        <p className="text-lg font-medium mb-3" style={{ color: "var(--text-primary)" }}>
          Analyzing Profile
        </p>

        <div className="h-6">
          <p className="text-sm" style={{
            color: "var(--text-secondary)",
            fontFamily: "'JetBrains Mono', monospace",
          }}>
            {MESSAGES[msgIdx]}
          </p>
        </div>

        {/* Progress dots */}
        <div className="flex gap-2 mt-8">
          {MESSAGES.map((_, i) => (
            <div
              key={i}
              className="w-2 h-2 rounded-full transition-all duration-500"
              style={{
                background: i <= msgIdx ? "var(--accent-blue)" : "var(--border)",
                transform: i <= msgIdx ? "scale(1)" : "scale(0.7)",
              }}
            />
          ))}
        </div>
      </div>

      <style jsx>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
