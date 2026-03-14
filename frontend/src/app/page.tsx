"use client";

import { useState, useCallback } from "react";
import { AnalyzeResponse } from "@/types";
import Dashboard from "@/components/Dashboard";
import SearchHero from "@/components/SearchHero";
import LoadingState from "@/components/LoadingState";
import ProfileHistory from "@/components/ProfileHistory";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [historyKey, setHistoryKey] = useState(0);

  const handleAnalyze = async (profile: string) => {
    setLoading(true);
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

      const result: AnalyzeResponse = await res.json();
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = useCallback(() => {
    setData(null);
    setError(null);
    setHistoryKey((k) => k + 1);
  }, []);

  return (
    <main className="relative z-10 min-h-screen">
      {!data && !loading && (
        <div className="flex flex-col min-h-screen">
          <SearchHero onSearch={handleAnalyze} error={error} />
          <div className="px-6 pb-12">
            <div className="w-full max-w-5xl mx-auto mb-4 flex justify-end">
              <a href="/pinned"
                className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg transition-all hover:brightness-125"
                style={{
                  background: "rgba(234,179,8,0.08)",
                  color: "#eab308",
                  border: "1px solid rgba(234,179,8,0.15)",
                  fontFamily: "'JetBrains Mono', monospace",
                }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"
                  stroke="currentColor" strokeWidth="2"
                  strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 17v5" />
                  <path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 1 1 0 0 0 1-1V4a2 2 0 0 0-2-2H9a2 2 0 0 0-2 2v1a1 1 0 0 0 1 1 1 1 0 0 1 1 1z" />
                </svg>
                Pinned Profiles
              </a>
            </div>
            <ProfileHistory key={historyKey} onSelectProfile={handleAnalyze} />
          </div>
        </div>
      )}
      {loading && <LoadingState />}
      {data && <Dashboard data={data} onReset={handleReset} />}
    </main>
  );
}
