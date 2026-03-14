"use client";

import { useState, useEffect } from "react";
import { AnalyzeResponse, ProfileHistoryEntry } from "@/types";
import StatsGrid from "./StatsGrid";
import CategoryChart from "./CategoryChart";
import TimingHeatmap from "./TimingHeatmap";
import SizeDistribution from "./SizeDistribution";
import StrengthsWeaknesses from "./StrengthsWeaknesses";
import TopMarkets from "./TopMarkets";
import Recommendations from "./Recommendations";
import StrategyProfile from "./StrategyProfile";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Props {
  data: AnalyzeResponse;
  onReset: () => void;
}

export default function Dashboard({ data, onReset }: Props) {
  const { profile, analysis, report, strategy } = data;
  const [pinned, setPinned] = useState(false);
  const [pinLoading, setPinLoading] = useState(false);

  // Check if this profile is pinned on mount
  useEffect(() => {
    fetch(`${API_URL}/api/history`)
      .then((r) => r.json())
      .then((entries: ProfileHistoryEntry[]) => {
        const match = entries.find((e) => e.wallet === profile.wallet);
        if (match) setPinned(!!match.pinned);
      })
      .catch(() => {});
  }, [profile.wallet]);

  const handlePin = async () => {
    setPinLoading(true);
    try {
      // Find the profile ID first
      const res = await fetch(`${API_URL}/api/history`);
      const entries: ProfileHistoryEntry[] = await res.json();
      const match = entries.find((e) => e.wallet === profile.wallet);
      if (match) {
        const pinRes = await fetch(`${API_URL}/api/history/${match.id}/pin`, { method: "PATCH" });
        const result = await pinRes.json();
        setPinned(result.pinned);
      }
    } catch {
      // silently fail
    } finally {
      setPinLoading(false);
    }
  };

  const profileUrl = profile.username
    ? `https://polymarket.com/@${profile.username}`
    : null;

  return (
    <div className="max-w-[1400px] mx-auto px-6 py-8">
      {/* Header */}
      <header className="flex items-center justify-between mb-8 animate-fade-up">
        <div className="flex items-center gap-4">
          <button onClick={onReset}
            className="p-2 rounded-lg transition-colors hover:brightness-125"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
              style={{ color: "var(--text-secondary)" }}>
              <path d="m15 18-6-6 6-6" />
            </svg>
          </button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-3">
              {profileUrl ? (
                <>
                  <a href={profileUrl} target="_blank" rel="noopener noreferrer"
                    className="stat-value hover:brightness-125 transition-all"
                    title="View on Polymarket">
                    @{profile.username || profile.wallet.slice(0, 10)}
                  </a>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                    strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                    style={{ color: "var(--text-muted)", marginTop: "2px" }}>
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                    <polyline points="15 3 21 3 21 9" />
                    <line x1="10" y1="14" x2="21" y2="3" />
                  </svg>
                </>
              ) : (
                <span className="stat-value">
                  @{profile.wallet.slice(0, 10)}
                </span>
              )}
            </h1>
            <p className="text-sm mt-0.5" style={{
              color: "var(--text-muted)",
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: "12px",
            }}>
              {profile.wallet}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Pin button */}
          <button
            onClick={handlePin}
            disabled={pinLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all hover:brightness-125"
            style={{
              background: pinned ? "rgba(234,179,8,0.15)" : "var(--bg-card)",
              border: `1px solid ${pinned ? "rgba(234,179,8,0.3)" : "var(--border)"}`,
              color: pinned ? "#eab308" : "var(--text-secondary)",
              fontFamily: "'JetBrains Mono', monospace",
            }}
            title={pinned ? "Unpin profile" : "Pin profile"}
          >
            <svg width="14" height="14" viewBox="0 0 24 24"
              fill={pinned ? "currentColor" : "none"}
              stroke="currentColor" strokeWidth="2"
              strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 17v5" />
              <path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 1 1 0 0 0 1-1V4a2 2 0 0 0-2-2H9a2 2 0 0 0-2 2v1a1 1 0 0 0 1 1 1 1 0 0 1 1 1z" />
            </svg>
            {pinned ? "Pinned" : "Pin"}
          </button>
          <div className="text-right">
            <p className="text-xs" style={{ color: "var(--text-muted)", fontFamily: "'JetBrains Mono', monospace" }}>
              {analysis.date_range[0]?.slice(0, 10)} &mdash; {analysis.date_range[1]?.slice(0, 10)}
            </p>
          </div>
        </div>
      </header>

      {/* Summary */}
      <div className="card-glow p-5 mb-6 animate-fade-up" style={{ animationDelay: "0.05s" }}>
        <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          {report.summary}
        </p>
      </div>

      {/* Key Stats */}
      <StatsGrid analysis={analysis} />

      {/* Strategy Profile */}
      {strategy && <StrategyProfile strategy={strategy} />}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <CategoryChart categories={analysis.category_breakdown} />
        <TimingHeatmap hours={analysis.timing.most_active_hours} days={analysis.timing.most_active_days} dailyHours={analysis.timing.daily_hours} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <SizeDistribution buckets={analysis.sizing.size_buckets} priceRanges={analysis.pricing.favorite_price_ranges} />
      </div>

      {/* Strengths & Weaknesses */}
      <StrengthsWeaknesses pros={report.pros} cons={report.cons} />

      {/* Top Markets */}
      <TopMarkets markets={analysis.market_summaries} />

      {/* Recommendations */}
      {report.recommendations.length > 0 && (
        <Recommendations items={report.recommendations} />
      )}
    </div>
  );
}
