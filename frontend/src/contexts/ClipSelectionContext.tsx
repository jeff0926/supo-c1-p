import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

interface ClipSelectionContextValue {
  selected: ReadonlySet<number>;
  toggle: (clipId: number) => void;
  clear: () => void;
  isSelected: (clipId: number) => boolean;
  count: number;
}

const ClipSelectionContext = createContext<ClipSelectionContextValue | null>(null);

interface ProviderProps {
  children: ReactNode;
}

export function ClipSelectionProvider({ children }: ProviderProps): JSX.Element {
  const [selected, setSelected] = useState<Set<number>>(new Set());

  const toggle = useCallback((clipId: number): void => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(clipId)) next.delete(clipId);
      else next.add(clipId);
      return next;
    });
  }, []);

  const clear = useCallback((): void => {
    setSelected(new Set());
  }, []);

  const isSelected = useCallback((clipId: number): boolean => selected.has(clipId), [selected]);

  const value = useMemo(
    () => ({ selected, toggle, clear, isSelected, count: selected.size }),
    [selected, toggle, clear, isSelected],
  );

  return (
    <ClipSelectionContext.Provider value={value}>{children}</ClipSelectionContext.Provider>
  );
}

export function useClipSelection(): ClipSelectionContextValue {
  const ctx = useContext(ClipSelectionContext);
  if (!ctx) {
    throw new Error("useClipSelection must be used inside ClipSelectionProvider");
  }
  return ctx;
}
