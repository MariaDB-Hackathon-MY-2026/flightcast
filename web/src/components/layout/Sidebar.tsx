"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Plane,
  Clock,
  LineChart,
  AlertTriangle,
  BookOpen,
  HelpCircle,
  Settings,
  PlayCircle,
} from "lucide-react";
import { useTour } from "@/components/tour/TourProvider";

const NAV = [
  { href: "/time-travel", label: "Time Travel", icon: Clock },
  { href: "/forecast-explorer", label: "Forecast Explorer", icon: LineChart },
  { href: "/coverage-drift", label: "Coverage Drift", icon: AlertTriangle },
  { href: "/how-it-works", label: "How It Works", icon: BookOpen },
];

export function Sidebar() {
  const pathname = usePathname();
  const { start, active } = useTour();

  return (
    <aside className="fc-sidebar w-60 shrink-0 px-3.5 py-5 flex flex-col">
      {/* ── Brand ─────────────────────────────────────────── */}
      <div className="px-1 mb-6">
        <div className="w-10 h-10 rounded-xl bg-accent-violet flex items-center justify-center shadow-md shadow-accent-violet/25">
          <Plane size={20} className="text-white" />
        </div>
      </div>

      {/* ── Navigation ────────────────────────────────────── */}
      <nav className="flex flex-col gap-0.5">
        {NAV.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-[14px] font-medium transition-colors ${
                isActive
                  ? "bg-accent-violet/[0.16] text-slate-50 border border-accent-violet/35"
                  : "text-slate-300 hover:bg-white/5 border border-transparent"
              }`}
            >
              <Icon
                size={18}
                className={isActive ? "text-accent-violet" : ""}
              />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* ── Pitch tour CTA ────────────────────────────────── */}
      <div className="mt-5 px-1">
        <button
          onClick={start}
          disabled={active}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg text-sm font-semibold bg-accent-violet text-white shadow-md disabled:opacity-50 disabled:cursor-not-allowed transition hover:brightness-110"
        >
          <PlayCircle size={14} />
          {active ? "Tour in progress" : "Start Pitch Tour"}
        </button>
      </div>

      <div className="flex-1" />

      {/* ── Help / Settings ────────────────────────────────── */}
      <nav className="flex flex-col gap-0.5 mb-3 pt-3 border-t border-white/5">
        <a
          href="https://github.com/imycc1221/flightcast"
          target="_blank"
          rel="noopener"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-400 hover:bg-white/5 hover:text-slate-200 transition"
        >
          <HelpCircle size={17} />
          Help
        </a>
        <a
          href="/how-it-works"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-400 hover:bg-white/5 hover:text-slate-200 transition"
        >
          <Settings size={17} />
          Settings
        </a>
      </nav>

      {/* ── Live status badge — refined, smaller ───────────── */}
      <div className="px-3 py-2 rounded-lg bg-emerald-500/[0.06] border border-emerald-500/20">
        <div className="flex items-center gap-2 text-xs">
          <span className="relative flex w-2 h-2">
            <span className="animate-ping absolute inline-flex w-full h-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex w-2 h-2 rounded-full bg-emerald-400" />
          </span>
          <span className="text-emerald-300 font-medium">Live</span>
        </div>
        <div className="text-[11px] text-slate-500 mt-0.5 ml-4">
          All systems operational
        </div>
      </div>
    </aside>
  );
}
