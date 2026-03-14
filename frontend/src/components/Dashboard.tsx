"use client";

import { AnalyzeResponse } from "@/types";
import StatsGrid from "./StatsGrid";
import BacktestMetrics from "./BacktestMetrics";
import PortfolioChart from "./PortfolioChart";
import CategoryChart from "./CategoryChart";
import TimingHeatmap from "./TimingHeatmap";
import SizeDistribution from "./SizeDistribution";
import StrengthsWeaknesses from "./StrengthsWeaknesses";
import TopMarkets from "./TopMarkets";
import Recommendations from "./Recommendations";
import StrategyProfile from "./StrategyProfile";

interface Props {
  data: AnalyzeResponse;
  onReset: () => void;
}

export default function Dashboard({ data, onReset }: Props) {
  const { profile, analysis, backtest, report, strategy } = data;

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
              <span className="stat-value">
                @{profile.username || profile.wallet.slice(0, 10)}
              </span>
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
        <div className="text-right">
          <p className="text-xs" style={{ color: "var(--text-muted)", fontFamily: "'JetBrains Mono', monospace" }}>
            {analysis.date_range[0]?.slice(0, 10)} &mdash; {analysis.date_range[1]?.slice(0, 10)}
          </p>
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

      {/* Backtest Metrics */}
      {backtest && <BacktestMetrics backtest={backtest} />}

      {/* Strategy Profile */}
      {strategy && <StrategyProfile strategy={strategy} />}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {backtest && <PortfolioChart snapshots={backtest.snapshots} />}
        <CategoryChart categories={analysis.category_breakdown} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <TimingHeatmap hours={analysis.timing.most_active_hours} days={analysis.timing.most_active_days} />
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
