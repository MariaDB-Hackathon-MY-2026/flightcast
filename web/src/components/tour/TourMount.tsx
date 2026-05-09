"use client";

import GuidedTour from "./GuidedTour";
import { useTour } from "./TourProvider";

/**
 * Mounts the tour overlay at the root layout. Reads active state from
 * TourContext so any component can call useTour().start().
 */
export function TourMount() {
  const { active, stop } = useTour();
  return <GuidedTour active={active} onComplete={stop} />;
}
