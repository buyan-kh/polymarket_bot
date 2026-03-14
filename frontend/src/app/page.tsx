"use client";

import { useState } from "react";
import { AnalyzeResponse } from "@/types";
import Dashboard from "@/components/Dashboard";
import SearchHero from "@/components/SearchHero";
import LoadingState from "@/components/LoadingState";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async (profile: string) => {
    setLoading(true);
    setError(null);
    setData(null);

    try {
      const res = await fetch(`${API_URL}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile, backtest: true }),
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

  const handleReset = () => {
    setData(null);
    setError(null);
  };

  return (
    <main className="relative z-10 min-h-screen">
      {!data && !loading && (
        <SearchHero onSearch={handleAnalyze} error={error} />
      )}
      {loading && <LoadingState />}
      {data && <Dashboard data={data} onReset={handleReset} />}
    </main>
  );
}
