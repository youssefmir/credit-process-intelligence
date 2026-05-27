/** Thème clair / sombre : préférence système, bascule manuelle mémorisée. */

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type Theme = "light" | "dark";
type Choice = Theme | "system";

interface ThemeState {
  theme: Theme;
  choice: Choice;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeState>({ theme: "light", choice: "system", toggle: () => {} });

const KEY = "cpi-theme";

function readChoice(): Choice {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" ? v : "system";
  } catch {
    return "system";
  }
}

function systemTheme(): Theme {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [choice, setChoice] = useState<Choice>(readChoice);
  const [system, setSystem] = useState<Theme>(systemTheme);

  useEffect(() => {
    const mq = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!mq) return;
    const onChange = () => setSystem(mq.matches ? "dark" : "light");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const theme: Theme = choice === "system" ? system : choice;

  useEffect(() => {
    const root = document.documentElement;
    if (choice === "system") delete root.dataset.theme;
    else root.dataset.theme = choice;
  }, [choice]);

  const toggle = useCallback(() => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setChoice(next);
    try {
      localStorage.setItem(KEY, next);
    } catch {
      /* stockage indisponible : la bascule reste valable pour la session */
    }
  }, [theme]);

  const value = useMemo(() => ({ theme, choice, toggle }), [theme, choice, toggle]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeState {
  return useContext(ThemeContext);
}

/** Lit les variables CSS courantes (après application du thème). */
export function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export interface Palette {
  bg: string;
  ink: string;
  ink2: string;
  muted: string;
  context: string;
  rule: string;
  grid: string;
  blue: string;
  green: string;
  red: string;
  yellow: string;
  grey: string;
  ctx: string;
  ord: string[];
  seq: string[];
  lineNominal: string;
  lineApproved: string;
  lineCancelled: string;
  lineDeclined: string;
  lineLoop: string;
  casing: string;
  stationFill: string;
  stationStroke: string;
}

export function readPalette(): Palette {
  const v = cssVar;
  return {
    bg: v("--bg"),
    ink: v("--ink"),
    ink2: v("--ink-2"),
    muted: v("--muted"),
    context: v("--context"),
    rule: v("--rule"),
    grid: v("--grid-line"),
    blue: v("--c-blue"),
    green: v("--c-green"),
    red: v("--c-red"),
    yellow: v("--c-yellow"),
    grey: v("--c-grey"),
    ctx: v("--c-context"),
    ord: [1, 2, 3, 4].map((i) => v(`--ord-${i}`)),
    seq: [1, 2, 3, 4, 5, 6, 7, 8].map((i) => v(`--seq-${i}`)),
    lineNominal: v("--line-nominal"),
    lineApproved: v("--line-approved"),
    lineCancelled: v("--line-cancelled"),
    lineDeclined: v("--line-declined"),
    lineLoop: v("--line-loop"),
    casing: v("--line-casing"),
    stationFill: v("--station-fill"),
    stationStroke: v("--station-stroke"),
  };
}

/** Palette relue à chaque changement de thème. */
export function usePalette(): Palette {
  const { theme } = useTheme();
  const [palette, setPalette] = useState<Palette>(() => readPalette());
  useEffect(() => {
    // Laisser le navigateur appliquer data-theme avant de relire les variables.
    const id = requestAnimationFrame(() => setPalette(readPalette()));
    return () => cancelAnimationFrame(id);
  }, [theme]);
  return palette;
}
