import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";

interface MasterPlayerContextValue {
  currentSrc: string | null;
  registerVideo: (el: HTMLVideoElement | null) => void;
  play: (src: string, seekSeconds: number) => void;
  seek: (seekSeconds: number) => void;
  clear: () => void;
}

const MasterPlayerContext = createContext<MasterPlayerContextValue | null>(null);

interface ProviderProps {
  children: ReactNode;
}

export function MasterPlayerProvider({ children }: ProviderProps): JSX.Element {
  const [currentSrc, setCurrentSrc] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const pendingSeekRef = useRef<number | null>(null);

  const registerVideo = useCallback((el: HTMLVideoElement | null): void => {
    videoRef.current = el;
    if (el && pendingSeekRef.current !== null) {
      const target = pendingSeekRef.current;
      pendingSeekRef.current = null;
      const onReady = (): void => {
        el.currentTime = target;
        el.removeEventListener("loadedmetadata", onReady);
      };
      if (el.readyState >= 1) {
        el.currentTime = target;
      } else {
        el.addEventListener("loadedmetadata", onReady);
      }
    }
  }, []);

  const seek = useCallback((seekSeconds: number): void => {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = seekSeconds;
    void v.play().catch(() => {
      /* autoplay blocked is fine — user can press play */
    });
  }, []);

  const play = useCallback(
    (src: string, seekSeconds: number): void => {
      if (src !== currentSrc) {
        setCurrentSrc(src);
        pendingSeekRef.current = seekSeconds;
      } else {
        seek(seekSeconds);
      }
    },
    [currentSrc, seek],
  );

  const clear = useCallback((): void => {
    const v = videoRef.current;
    if (v) {
      v.pause();
      v.removeAttribute("src");
      v.load();
    }
    pendingSeekRef.current = null;
    setCurrentSrc(null);
  }, []);

  const value = useMemo(
    () => ({ currentSrc, registerVideo, play, seek, clear }),
    [currentSrc, registerVideo, play, seek, clear],
  );

  return <MasterPlayerContext.Provider value={value}>{children}</MasterPlayerContext.Provider>;
}

export function useMasterPlayer(): MasterPlayerContextValue {
  const ctx = useContext(MasterPlayerContext);
  if (!ctx) {
    throw new Error("useMasterPlayer must be used inside MasterPlayerProvider");
  }
  return ctx;
}
