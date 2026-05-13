"use client";

/**
 * GuidedTour — pitch-tour overlay engine.
 *
 * Behavior contract (per user requirements):
 *   1. Spotlight + popover. Popover NEVER overlaps the highlighted element —
 *      auto-picks the side with the most viewport space.
 *   2. The user can navigate freely (sidebar nav, in-page links, etc.) without
 *      changing the tour's step. Tour state persists. The engine only forces
 *      a navigation ONCE per Next/Back click, not on every render.
 *   3. The user can click underlying cards / buttons / inputs without
 *      dismissing the tour. The full-screen overlay is pointer-events: none;
 *      only the popover (and its X button) capture clicks.
 *   4. If the user navigates away from the current step's page, the highlight
 *      gracefully disappears but the popover stays visible (in a fixed corner)
 *      so the user knows the tour is still active.
 *
 * Pattern: TOUR_STEPS = source of truth, GuidedTour reads it, popover content
 * comes from each step.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { TOUR_STEPS, type TourStep } from "./TOUR_STEPS";

interface Coords {
  top: number;
  left: number;
  width: number;
  height: number;
}

const POPOVER_WIDTH = 340;
// Conservative estimate — actual popover renders at ~200-220px once content
// flows. Using a smaller value here makes the auto-placer find "fits" more
// often, avoiding the fallback corner that was overlapping cards near the
// viewport edge.
const POPOVER_HEIGHT_EST = 220;
const GAP = 18;
const VIEWPORT_PAD = 14;

type Side = "bottom" | "top" | "right" | "left" | "fallback";

/**
 * Pick the side of the highlighted element that has enough room for the
 * popover, without overlapping. Preference order: bottom → right → top →
 * left → fallback (top-right corner of viewport).
 */
function pickPopoverPlacement(
  c: Coords,
  vw: number,
  vh: number,
): { top: number; left: number; side: Side } {
  const spaceBottom = vh - (c.top + c.height) - GAP - VIEWPORT_PAD;
  const spaceTop = c.top - GAP - VIEWPORT_PAD;
  const spaceRight = vw - (c.left + c.width) - GAP - VIEWPORT_PAD;
  const spaceLeft = c.left - GAP - VIEWPORT_PAD;

  let side: Side;
  if (spaceBottom >= POPOVER_HEIGHT_EST) side = "bottom";
  else if (spaceRight >= POPOVER_WIDTH) side = "right";
  else if (spaceTop >= POPOVER_HEIGHT_EST) side = "top";
  else if (spaceLeft >= POPOVER_WIDTH) side = "left";
  else side = "fallback";

  if (side === "fallback") {
    return {
      top: VIEWPORT_PAD,
      left: vw - POPOVER_WIDTH - VIEWPORT_PAD,
      side,
    };
  }

  let top: number;
  let left: number;
  if (side === "bottom") {
    top = c.top + c.height + GAP;
    left = c.left;
  } else if (side === "top") {
    top = c.top - POPOVER_HEIGHT_EST - GAP;
    left = c.left;
  } else if (side === "right") {
    top = c.top;
    left = c.left + c.width + GAP;
  } else {
    top = c.top;
    left = c.left - POPOVER_WIDTH - GAP;
  }

  // Clamp the perpendicular axis only — never let clamping push the popover
  // back over the highlighted element.
  if (side === "bottom" || side === "top") {
    left = Math.max(
      VIEWPORT_PAD,
      Math.min(left, vw - POPOVER_WIDTH - VIEWPORT_PAD),
    );
  } else {
    top = Math.max(
      VIEWPORT_PAD,
      Math.min(top, vh - POPOVER_HEIGHT_EST - VIEWPORT_PAD),
    );
  }
  return { top, left, side };
}

interface Props {
  active: boolean;
  onComplete: () => void;
}

export default function GuidedTour({ active, onComplete }: Props) {
  const [step, setStep] = useState(0);
  const [coords, setCoords] = useState<Coords | null>(null);
  const router = useRouter();
  const pathname = usePathname();

  // Track the last step we've ALREADY navigated for. Without this, every
  // re-render with a pathname change would re-fire the navigation, fighting
  // the user when they manually navigate.
  const lastNavStep = useRef<number>(-1);

  /**
   * Scroll the page so the target element is in view, THEN measure.
   * Called ONCE per step change — never on user-initiated scrolling.
   */
  const scrollAndMeasure = useCallback((stepIdx: number) => {
    const s = TOUR_STEPS[stepIdx];
    const el = document.querySelector<HTMLElement>(s.target);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      // Defer one frame so getBoundingClientRect reads post-scroll position
      requestAnimationFrame(() => {
        const r = el.getBoundingClientRect();
        setCoords({
          top: r.top,
          left: r.left,
          width: r.width,
          height: r.height,
        });
      });
    } else {
      // Anchor not on this page → highlight hides, popover stays in fallback
      setCoords(null);
    }
  }, []);

  /**
   * Measure WITHOUT scrolling — used by the scroll/resize listener so the
   * highlight + popover follow the user as they scroll the page freely,
   * without the engine yanking them back to the original step element.
   */
  const measureOnly = useCallback((stepIdx: number) => {
    const s = TOUR_STEPS[stepIdx];
    const el = document.querySelector<HTMLElement>(s.target);
    if (el) {
      const r = el.getBoundingClientRect();
      setCoords({
        top: r.top,
        left: r.left,
        width: r.width,
        height: r.height,
      });
    } else {
      setCoords(null);
    }
  }, []);

  // Reset on open
  useEffect(() => {
    if (active) {
      setStep(0);
      setCoords(null);
      lastNavStep.current = -1;
    }
  }, [active]);

  // Navigate (one-shot per step) + scroll-and-measure
  useEffect(() => {
    if (!active) return;
    const s = TOUR_STEPS[step];
    setCoords(null);

    if (lastNavStep.current !== step) {
      lastNavStep.current = step;
      if (s.route && s.route !== pathname) {
        router.push(s.route);
        const t = setTimeout(() => scrollAndMeasure(step), 380);
        return () => clearTimeout(t);
      }
    }
    // Either same step (user navigated manually) or already on the right page
    const t = setTimeout(() => scrollAndMeasure(step), 60);
    return () => clearTimeout(t);
  }, [step, active, pathname, router, scrollAndMeasure]);

  // Re-measure on resize / scroll — uses measureOnly (no scrollIntoView!)
  // so the user can scroll freely and the highlight + popover follow.
  useEffect(() => {
    if (!active) return;
    const handler = () => measureOnly(step);
    window.addEventListener("resize", handler);
    window.addEventListener("scroll", handler, { passive: true });
    return () => {
      window.removeEventListener("resize", handler);
      window.removeEventListener("scroll", handler);
    };
  }, [active, step, measureOnly]);

  if (!active) return null;
  const currentStep: TourStep = TOUR_STEPS[step];
  const total = TOUR_STEPS.length;

  // ─── Popover placement ──────────────────────────────────────────────
  let popTop: number;
  let popLeft: number;
  let popSide: Side;
  let highlightVisible = false;

  if (coords && typeof window !== "undefined") {
    const placement = pickPopoverPlacement(
      coords,
      window.innerWidth,
      window.innerHeight,
    );
    popTop = placement.top;
    popLeft = placement.left;
    popSide = placement.side;
    highlightVisible = coords.width > 0 && coords.height > 0;
  } else {
    // Anchor missing → fallback floating popover in top-right corner
    popTop = VIEWPORT_PAD;
    popLeft =
      typeof window !== "undefined"
        ? window.innerWidth - POPOVER_WIDTH - VIEWPORT_PAD
        : 100;
    popSide = "fallback";
  }

  return (
    <div className="tour-overlay" aria-live="polite">
      {/* Spotlight: punch-through shadow trick from §5.1 of the template.
          pointer-events: none — clicks pass through to underlying elements. */}
      {highlightVisible && coords && (
        <div
          className="tour-highlight"
          style={{
            top: coords.top - 8,
            left: coords.left - 8,
            width: coords.width + 16,
            height: coords.height + 16,
          }}
        />
      )}

      {/* Popover — pointer-events: auto so its buttons work; everything else
          on the overlay layer is pointer-events: none. */}
      <div
        className={`tour-popover tour-popover--${popSide}`}
        style={{ top: popTop, left: popLeft, width: POPOVER_WIDTH }}
        role="dialog"
        aria-label={`Pitch tour step ${step + 1} of ${total}: ${currentStep.title}`}
      >
        <button
          className="tour-close"
          onClick={onComplete}
          aria-label="Close tour"
          type="button"
        >
          <X size={16} aria-hidden="true" />
        </button>

        <div className="tour-step-indicator">
          Step {step + 1} of {total}
        </div>
        <h3 className="tour-title">{currentStep.title}</h3>
        <p className="tour-content">{currentStep.content}</p>

        {!highlightVisible && (
          <p className="tour-hint">
            Tour active — navigate back to the step&apos;s page to see the
            highlight.
          </p>
        )}

        <div className="tour-footer">
          <button
            className="tour-btn tour-btn--secondary"
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0}
            type="button"
          >
            <ChevronLeft size={14} aria-hidden="true" /> Back
          </button>

          {step < total - 1 ? (
            <button
              className="tour-btn tour-btn--primary"
              onClick={() => setStep((s) => s + 1)}
              type="button"
            >
              Next <ChevronRight size={14} aria-hidden="true" />
            </button>
          ) : (
            <button
              className="tour-btn tour-btn--primary"
              onClick={onComplete}
              type="button"
            >
              Finish Tour
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
