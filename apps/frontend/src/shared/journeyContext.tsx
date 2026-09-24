import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { DirectorBuildPlan, OrchestrationSession } from "./types";
import { journeySnapshot, type JourneySnapshot } from "./productionJourney";

export interface JourneySignals {
  plan: DirectorBuildPlan | null;
  session: OrchestrationSession | null;
  executionStatus: string;
  reviewPending: number;
  qaStatus: string;
}

const EMPTY: JourneySignals = { plan: null, session: null, executionStatus: "", reviewPending: 0, qaStatus: "" };

const JourneyContext = createContext<{ snapshot: JourneySnapshot; update: (patch: Partial<JourneySignals>) => void } | null>(null);

export function JourneyProvider({ children }: { children: ReactNode }) {
  const [signals, setSignals] = useState<JourneySignals>(EMPTY);
  const update = useCallback((patch: Partial<JourneySignals>) => {
    setSignals((current) => {
      const entries = Object.entries(patch) as Array<[keyof JourneySignals, JourneySignals[keyof JourneySignals]]>;
      if (entries.every(([key, value]) => Object.is(current[key], value))) return current;
      return { ...current, ...patch };
    });
  }, []);
  const value = useMemo(() => ({ snapshot: journeySnapshot(signals), update }), [signals, update]);
  return <JourneyContext.Provider value={value}>{children}</JourneyContext.Provider>;
}

export function useJourney() {
  const value = useContext(JourneyContext);
  if (!value) throw new Error("useJourney must render inside JourneyProvider");
  return value;
}
