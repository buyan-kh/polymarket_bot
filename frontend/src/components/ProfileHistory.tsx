"use client";

import { useState, useEffect, useRef } from "react";
import { ProfileHistoryEntry } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type SortKey = "analyzed_at" | "total_volume" | "total_return_pct" | "win_rate" | "sharpe_ratio";
type SortDir = "asc" | "desc";

interface Props {
  onSelectProfile: (profile: string) => void;
}

function fmtVolume(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(0)}`;
}

function fmtPct(n: number | null): string {
  if (n === null || n === undefined) return "--";
  return `${n >= 0 ? "+" : ""}${n.toFixed(1)}%`;
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function ProfileHistory({ onSelectProfile }: Props) {
  const [entries, setEntries] = useState<ProfileHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState<SortKey>("analyzed_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");
  const notesRef = useRef<HTMLInputElement>(null);

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_URL}/api/history`);
      if (res.ok) {
        const data: ProfileHistoryEntry[] = await res.json();
        setEntries(data);
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  useEffect(() => {
    if (editingId !== null && notesRef.current) {
      notesRef.current.focus();
    }
  }, [editingId]);

  const handleDelete = async (id: number) => {
    try {
      await fetch(`${API_URL}/api/history/${id}`, { method: "DELETE" });
      setEntries((prev) => prev.filter((e) => e.id !== id));
    } catch {
      // silently fail
    }
  };

  const handleTogglePin = async (id: number) => {
    try {
      const res = await fetch(`${API_URL}/api/history/${id}/pin`, { method: "PATCH" });
      const result = await res.json();
      setEntries((prev) =>
        prev.map((e) => (e.id === id ? { ...e, pinned: result.pinned } : e))
      );
    } catch {
      // silently fail
    }
  };

  const handleNotesBlur = async (id: number) => {
    setEditingId(null);
    try {
      await fetch(`${API_URL}/api/history/${id}/notes`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes: editValue }),
      });
      setEntries((prev) =>
        prev.map((e) => (e.id === id ? { ...e, notes: editValue } : e))
      );
    } catch {
      // silently fail
    }
  };

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const sorted = [...entries].sort((a, b) => {
    // Pinned profiles always come first
    if (a.pinned && !b.pinned) return -1;
    if (!a.pinned && b.pinned) return 1;
    const dir = sortDir === "asc" ? 1 : -1;
    const aVal = a[sortKey];
    const bVal = b[sortKey];
    if (aVal === null && bVal === null) return 0;
    if (aVal === null) return 1;
    if (bVal === null) return -1;
    if (typeof aVal === "string" && typeof bVal === "string") {
      return aVal.localeCompare(bVal) * dir;
    }
    return ((aVal as number) - (bVal as number)) * dir;
  });

  if (loading) return null;
  if (entries.length === 0) return null;

  const SortArrow = ({ col }: { col: SortKey }) => {
    if (sortKey !== col) return null;
    return (
      <span className="ml-1 inline-block" style={{ fontSize: "10px" }}>
        {sortDir === "desc" ? "\u2193" : "\u2191"}
      </span>
    );
  };

  const thStyle: React.CSSProperties = {
    color: "var(--text-muted)",
    cursor: "pointer",
    userSelect: "none",
  };

  return (
    <div
      className="w-full max-w-5xl mx-auto mt-10 mb-8 animate-fade-up"
      style={{ animationDelay: "0.5s" }}
    >
      <div className="card-glow p-5">
        <div className="flex items-center gap-3 mb-4">
          <div
            className="w-1.5 h-5 rounded-full"
            style={{ background: "var(--accent-violet)" }}
          />
          <h2
            className="text-sm font-semibold uppercase tracking-widest"
            style={{ color: "var(--text-secondary)" }}
          >
            Profile History
          </h2>
          <span
            className="ml-auto text-xs px-2 py-0.5 rounded-full"
            style={{
              background: "rgba(139,92,246,0.1)",
              color: "var(--accent-violet)",
              border: "1px solid rgba(139,92,246,0.2)",
            }}
          >
            {entries.length} saved
          </span>
        </div>

        <div className="overflow-x-auto">
          <table
            className="w-full text-sm"
            style={{ fontFamily: "'JetBrains Mono', monospace" }}
          >
            <thead>
              <tr>
                <th className="py-2 pr-2 text-xs font-normal w-8" style={{ color: "var(--text-muted)" }} />
                <th className="text-left py-2 pr-4 text-xs font-normal" style={thStyle}>
                  Profile
                </th>
                <th
                  className="text-right py-2 px-3 text-xs font-normal"
                  style={thStyle}
                  onClick={() => handleSort("total_volume")}
                >
                  Volume
                  <SortArrow col="total_volume" />
                </th>
                <th
                  className="text-right py-2 px-3 text-xs font-normal"
                  style={thStyle}
                  onClick={() => handleSort("total_return_pct")}
                >
                  Return
                  <SortArrow col="total_return_pct" />
                </th>
                <th
                  className="text-right py-2 px-3 text-xs font-normal"
                  style={thStyle}
                  onClick={() => handleSort("win_rate")}
                >
                  Win Rate
                  <SortArrow col="win_rate" />
                </th>
                <th
                  className="text-right py-2 px-3 text-xs font-normal"
                  style={thStyle}
                  onClick={() => handleSort("sharpe_ratio")}
                >
                  Sharpe
                  <SortArrow col="sharpe_ratio" />
                </th>
                <th
                  className="text-right py-2 px-3 text-xs font-normal"
                  style={thStyle}
                  onClick={() => handleSort("analyzed_at")}
                >
                  Analyzed
                  <SortArrow col="analyzed_at" />
                </th>
                <th className="text-left py-2 px-3 text-xs font-normal" style={{ color: "var(--text-muted)" }}>
                  Notes
                </th>
                <th className="py-2 pl-3 text-xs font-normal" style={{ color: "var(--text-muted)" }} />
              </tr>
            </thead>
            <tbody>
              {sorted.map((entry) => {
                const returnColor =
                  entry.total_return_pct === null
                    ? "var(--text-muted)"
                    : entry.total_return_pct >= 0
                    ? "var(--accent-green)"
                    : "var(--accent-red)";

                return (
                  <tr
                    key={entry.id}
                    className="transition-colors group"
                    style={{ borderTop: "1px solid var(--border)" }}
                  >
                    {/* Pin toggle */}
                    <td className="py-2.5 pr-2 text-center">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleTogglePin(entry.id);
                        }}
                        className="p-0.5 rounded transition-all hover:brightness-125"
                        style={{ color: entry.pinned ? "#eab308" : "var(--text-muted)" }}
                        title={entry.pinned ? "Unpin" : "Pin"}
                      >
                        <svg width="13" height="13" viewBox="0 0 24 24"
                          fill={entry.pinned ? "currentColor" : "none"}
                          stroke="currentColor" strokeWidth="2"
                          strokeLinecap="round" strokeLinejoin="round">
                          <path d="M12 17v5" />
                          <path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 1 1 0 0 0 1-1V4a2 2 0 0 0-2-2H9a2 2 0 0 0-2 2v1a1 1 0 0 0 1 1 1 1 0 0 1 1 1z" />
                        </svg>
                      </button>
                    </td>

                    {/* Profile name - clickable */}
                    <td className="py-2.5 pr-4 text-xs">
                      <button
                        onClick={() =>
                          onSelectProfile(entry.username || entry.wallet)
                        }
                        className="text-left hover:brightness-125 transition-all"
                        style={{ color: "var(--accent-blue)" }}
                        title={`Re-analyze ${entry.username || entry.wallet}`}
                      >
                        <span className="font-medium">
                          @{entry.username || entry.wallet.slice(0, 10) + "..."}
                        </span>
                        <span
                          className="block text-[10px] mt-0.5"
                          style={{ color: "var(--text-muted)" }}
                        >
                          {entry.total_trades.toLocaleString()} trades
                        </span>
                      </button>
                    </td>

                    {/* Volume */}
                    <td
                      className="py-2.5 px-3 text-right text-xs"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      {fmtVolume(entry.total_volume)}
                    </td>

                    {/* Return */}
                    <td
                      className="py-2.5 px-3 text-right text-xs font-medium"
                      style={{ color: returnColor }}
                    >
                      {fmtPct(entry.total_return_pct)}
                    </td>

                    {/* Win Rate */}
                    <td
                      className="py-2.5 px-3 text-right text-xs"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      {entry.win_rate !== null && entry.win_rate !== undefined
                        ? `${(entry.win_rate * 100).toFixed(1)}%`
                        : "--"}
                    </td>

                    {/* Sharpe */}
                    <td
                      className="py-2.5 px-3 text-right text-xs"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      {entry.sharpe_ratio !== null && entry.sharpe_ratio !== undefined
                        ? entry.sharpe_ratio.toFixed(2)
                        : "--"}
                    </td>

                    {/* Analyzed date */}
                    <td
                      className="py-2.5 px-3 text-right text-xs"
                      style={{ color: "var(--text-muted)" }}
                    >
                      {fmtDate(entry.analyzed_at)}
                    </td>

                    {/* Notes - inline editable */}
                    <td className="py-2.5 px-3 text-xs max-w-[180px]">
                      {editingId === entry.id ? (
                        <input
                          ref={notesRef}
                          type="text"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          onBlur={() => handleNotesBlur(entry.id)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleNotesBlur(entry.id);
                            if (e.key === "Escape") setEditingId(null);
                          }}
                          className="w-full bg-transparent outline-none px-1.5 py-0.5 rounded"
                          style={{
                            color: "var(--text-primary)",
                            border: "1px solid var(--accent-blue)",
                            fontSize: "11px",
                          }}
                        />
                      ) : (
                        <button
                          onClick={() => {
                            setEditingId(entry.id);
                            setEditValue(entry.notes || "");
                          }}
                          className="text-left truncate w-full px-1.5 py-0.5 rounded transition-colors hover:brightness-125"
                          style={{
                            color: entry.notes
                              ? "var(--text-secondary)"
                              : "var(--text-muted)",
                            border: "1px solid transparent",
                            fontSize: "11px",
                          }}
                          title="Click to edit notes"
                        >
                          {entry.notes || "add note..."}
                        </button>
                      )}
                    </td>

                    {/* Delete */}
                    <td className="py-2.5 pl-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(entry.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:brightness-125"
                        style={{ color: "var(--accent-red)" }}
                        title="Remove from history"
                      >
                        <svg
                          width="14"
                          height="14"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M3 6h18" />
                          <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                          <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
                        </svg>
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
