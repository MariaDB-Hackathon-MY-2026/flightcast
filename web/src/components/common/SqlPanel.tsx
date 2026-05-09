"use client";

import { useState, type ReactNode } from "react";
import { ChevronDown, Copy, Check } from "lucide-react";

const SQL_KEYWORDS = new Set([
  "SELECT", "FROM", "WHERE", "AND", "OR", "ORDER", "BY", "GROUP", "JOIN",
  "INNER", "LEFT", "RIGHT", "FULL", "ON", "AS", "NULL", "IS", "NOT", "IN",
  "BETWEEN", "LIKE", "UNION", "INSERT", "UPDATE", "DELETE", "CREATE",
  "ALTER", "DROP", "FOR", "SYSTEM_TIME", "OF", "ALL", "AVG", "COUNT", "SUM",
  "MIN", "MAX", "CONCAT", "ROUND", "LIMIT", "DISTINCT", "WITH", "VERSIONING",
]);

/**
 * Lightweight SQL syntax highlighter — keyword/string/number/comment.
 * Token regex (order matters):
 *   1. line comment  --…
 *   2. quoted string '…' or "…"
 *   3. number (int or decimal)
 *   4. identifier / keyword
 *   5. whitespace
 *   6. fallback single char
 */
function highlightSql(sql: string): ReactNode[] {
  const TOKEN_RE = /(--[^\n]*|'(?:[^']|'')*'|"(?:[^"]|"")*"|\b\d+(?:\.\d+)?\b|\b\w+\b|\s+|.)/g;
  const tokens = sql.match(TOKEN_RE) ?? [];
  return tokens.map((t, i) => {
    if (t.startsWith("--")) return <span key={i} className="com">{t}</span>;
    if (t.startsWith("'") || t.startsWith('"'))
      return <span key={i} className="str">{t}</span>;
    if (/^\d/.test(t)) return <span key={i} className="num">{t}</span>;
    if (SQL_KEYWORDS.has(t.toUpperCase()))
      return <span key={i} className="kw">{t}</span>;
    return <span key={i}>{t}</span>;
  });
}

interface Props {
  /** Plain SQL string — gets auto-highlighted on render. */
  sql: string;
  /** Header title (left side of the summary bar). Defaults to "View the live MariaDB query". */
  title?: string;
  /** Whether to render the panel open by default. */
  defaultOpen?: boolean;
}

/**
 * SqlPanel — accordion-style card holding a syntax-highlighted SQL block.
 * Has TWO copy affordances: one in the header (always visible) and one
 * inside the code block itself (top-right of the code).
 */
export function SqlPanel({
  sql,
  title = "View the live MariaDB query",
  defaultOpen = true,
}: Props) {
  const [copiedHeader, setCopiedHeader] = useState(false);
  const [copiedInline, setCopiedInline] = useState(false);

  const handleCopy = async (which: "header" | "inline") => {
    try {
      await navigator.clipboard.writeText(sql);
      if (which === "header") {
        setCopiedHeader(true);
        setTimeout(() => setCopiedHeader(false), 1500);
      } else {
        setCopiedInline(true);
        setTimeout(() => setCopiedInline(false), 1500);
      }
    } catch {
      // Clipboard write blocked — silently no-op (user can still
      // select-and-copy manually).
    }
  };

  return (
    <details className="fc-stat group" open={defaultOpen}>
      <summary className="cursor-pointer flex items-center justify-between text-slate-100 font-semibold list-none gap-3">
        <span className="flex items-center gap-2 text-[15px]">
          <ChevronDown
            size={16}
            className="text-slate-400 transition-transform group-open:rotate-0 -rotate-90"
          />
          {title}
        </span>
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            handleCopy("header");
          }}
          aria-label="Copy SQL query to clipboard"
          title="Copy SQL"
          className="p-1.5 rounded-md text-slate-400 hover:bg-white/[0.05] hover:text-slate-200 transition"
        >
          {copiedHeader ? (
            <Check size={16} className="text-emerald-400" aria-hidden="true" />
          ) : (
            <Copy size={16} aria-hidden="true" />
          )}
        </button>
      </summary>

      <div className="relative mt-4">
        <pre className="fc-codeblock m-0">{highlightSql(sql)}</pre>
        <button
          type="button"
          onClick={() => handleCopy("inline")}
          aria-label="Copy SQL query to clipboard"
          title="Copy SQL"
          className="absolute top-2 right-2 p-1.5 rounded-md text-slate-500 hover:bg-white/[0.05] hover:text-slate-200 transition"
        >
          {copiedInline ? (
            <Check size={14} className="text-emerald-400" aria-hidden="true" />
          ) : (
            <Copy size={14} aria-hidden="true" />
          )}
        </button>
      </div>
    </details>
  );
}
