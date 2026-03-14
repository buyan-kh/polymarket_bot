"use client";

import { useState, useEffect, useCallback } from "react";
import { AnalyzeResponse, ProfileHistoryEntry } from "@/types";
import Dashboard from "@/components/Dashboard";
import LoadingState from "@/components/LoadingState";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function fmtVolume(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(0)}`;
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export default function PinnedPage() {
  const [pinned, setPinned] = useState<ProfileHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchPinned = async () => {
    try {
      const res = await fetch(`${API_URL}/api/pinned`);
      if (res.ok) setPinned(await res.json());
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPinned();
  }, []);

  const handleAnalyze = async (profile: string) => {
    setAnalyzing(true);
    setError(null);
    setData(null);
    try {
      const res = await fetch(`${API_URL}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      setData(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleReset = useCallback(() => {
    setData(null);
    setError(null);
    fetchPinned();
  }, []);

  const handleUnpin = async (id: number) => {
    try {
      await fetch(`${API_URL}/api/history/${id}/pin`, { method: "PATCH" });
      setPinned((prev) => prev.filter((e) => e.id !== id));
    } catch {
      // silently fail
    }
  };

  if (analyzing) return <LoadingState />;
  if (data) return <Dashboard data={data} onReset={handleReset} />;

  return (
    <main className="relative z-10 min-h-screen">
      <div className="max-w-[1100px] mx-auto px-6 py-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <a href="/"
              className="p-2 rounded-lg transition-colors hover:brightness-125"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                style={{ color: "var(--text-secondary)" }}>
                <path d="m15 18-6-6 6-6" />
              </svg>
            </a>
            <div>
              <h1 className="text-xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>
                Pinned Profiles
              </h1>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                Traders you're tracking
              </p>
            </div>
          </div>
          <span className="text-xs px-2.5 py-1 rounded-full"
            style={{
              background: "rgba(234,179,8,0.1)",
              color: "#eab308",
              border: "1px solid rgba(234,179,8,0.2)",
              fontFamily: "'JetBrains Mono', monospace",
            }}>
            {pinned.length} pinned
          </span>
        </div>

        {error && (
          <div className="card-glow p-4 mb-6" style={{ borderColor: "var(--accent-red)" }}>
            <p className="text-sm" style={{ color: "var(--accent-red)" }}>{error}</p>
          </div>
        )}

        {loading ? (
          <div className="text-center py-20" style={{ color: "var(--text-muted)" }}>
            Loading...
          </div>
        ) : pinned.length === 0 ? (
          <div className="card-glow p-10 text-center">
            <p className="text-sm mb-2" style={{ color: "var(--text-secondary)" }}>
              No pinned profiles yet.
            </p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Analyze a profile and click the pin button to track them here.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {pinned.map((entry) => (
              <div key={entry.id} className="card-glow p-5 transition-all hover:brightness-110 group relative">
                {/* Unpin button */}
                <button
                  onClick={() => handleUnpin(entry.id)}
                  className="absolute top-3 right-3 p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity hover:brightness-125"
                  style={{ color: "#eab308" }}
                  title="Unpin"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"
                    stroke="currentColor" strokeWidth="2"
                    strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 17v5" />
                    <path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 1 1 0 0 0 1-1V4a2 2 0 0 0-2-2H9a2 2 0 0 0-2 2v1a1 1 0 0 0 1 1 1 1 0 0 1 1 1z" />
                  </svg>
                </button>

                {/* Profile name */}
                <button
                  onClick={() => handleAnalyze(entry.username || entry.wallet)}
                  className="text-left w-full"
                >
                  <h3 className="text-base font-semibold hover:brightness-125 transition-all"
                    style={{ color: "var(--accent-blue)" }}>
                    @{entry.username || entry.wallet.slice(0, 12) + "..."}
                  </h3>
                </button>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-3 mt-4"
                  style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                  <div>
                    <p className="text-[10px] uppercase tracking-wider mb-0.5"
                      style={{ color: "var(--text-muted)" }}>Volume</p>
                    <p className="text-sm font-medium"
                      style={{ color: "var(--text-secondary)" }}>
                      {fmtVolume(entry.total_volume)}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-wider mb-0.5"
                      style={{ color: "var(--text-muted)" }}>Trades</p>
                    <p className="text-sm font-medium"
                      style={{ color: "var(--text-secondary)" }}>
                      {entry.total_trades.toLocaleString()}
                    </p>
                  </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between mt-4 pt-3"
                  style={{ borderTop: "1px solid var(--border)" }}>
                  <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                    Last analyzed: {fmtDate(entry.analyzed_at)}
                  </p>
                  <button
                    onClick={() => handleAnalyze(entry.username || entry.wallet)}
                    className="text-[10px] px-2 py-0.5 rounded transition-all hover:brightness-125"
                    style={{
                      background: "rgba(59,130,246,0.1)",
                      color: "var(--accent-blue)",
                      border: "1px solid rgba(59,130,246,0.2)",
                    }}
                  >
                    Analyze
                  </button>
                </div>

                {/* Notes */}
                {entry.notes && (
                  <p className="text-[10px] mt-2 italic"
                    style={{ color: "var(--text-muted)" }}>
                    {entry.notes}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
