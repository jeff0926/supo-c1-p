import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

interface ActiveClipContextValue {
  activeClipId: number | null;
  setActiveClipId: (id: number | null) => void;
}

const ActiveClipContext = createContext<ActiveClipContextValue | null>(null);

interface ProviderProps {
  children: ReactNode;
}

export function ActiveClipProvider({ children }: ProviderProps): JSX.Element {
  const [activeClipId, setActive] = useState<number | null>(null);

  const setActiveClipId = useCallback((id: number | null): void => {
    setActive(id);
  }, []);

  const value = useMemo(
    () => ({ activeClipId, setActiveClipId }),
    [activeClipId, setActiveClipId],
  );

  return <ActiveClipContext.Provider value={value}>{children}</ActiveClipContext.Provider>;
}

export function useActiveClip(): ActiveClipContextValue {
  const ctx = useContext(ActiveClipContext);
  if (!ctx) {
    throw new Error("useActiveClip must be used inside ActiveClipProvider");
  }
  return ctx;
}
