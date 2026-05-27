import { motion, useReducedMotion, useScroll, useSpring } from "motion/react";
import { useEffect, useState } from "react";

import { REPO_URL, SECTIONS } from "../content/sections";
import { useTheme } from "../lib/theme";

export default function Header() {
  const { theme, toggle } = useTheme();
  const reduced = useReducedMotion();
  const { scrollYProgress } = useScroll();
  const smooth = useSpring(scrollYProgress, { stiffness: 220, damping: 40, mass: 0.3 });
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState<string>("");

  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const els = SECTIONS.map((s) => document.getElementById(s.id)).filter(Boolean) as HTMLElement[];
    const io = new IntersectionObserver(
      (entries) => {
        const vis = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (vis[0]) setActive(vis[0].target.id);
      },
      { rootMargin: "-20% 0px -70% 0px" },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  return (
    <header className="topbar">
      <motion.div className="progress" style={{ scaleX: reduced ? scrollYProgress : smooth }} aria-hidden="true" />
      <div className="wrap topbar-inner">
        <a className="brand" href="#top" aria-label="Retour au début de l'étude">
          <svg width="26" height="18" viewBox="0 0 26 18" aria-hidden="true">
            <path d="M1 9 H25" stroke="var(--line-nominal)" strokeWidth="5" />
            <circle cx="13" cy="9" r="5" fill="var(--station-fill)" stroke="var(--station-stroke)" strokeWidth="2.5" />
          </svg>
          <span>Credit Process Intelligence</span>
        </a>
        <nav aria-label="Sommaire" className={`toc ${open ? "open" : ""}`}>
          <button type="button" className="toc-toggle" aria-expanded={open} aria-controls="toc-list" onClick={() => setOpen((v) => !v)}>
            Sommaire
          </button>
          <ol id="toc-list">
            {SECTIONS.map((s) => (
              <li key={s.id}>
                <a href={`#${s.id}`} aria-current={active === s.id ? "true" : undefined} onClick={() => setOpen(false)} title={s.short}>
                  <span className="toc-num">{s.num}</span>
                  <span className="toc-label">{s.short}</span>
                </a>
              </li>
            ))}
          </ol>
        </nav>
        <div className="topbar-actions">
          <button type="button" className="icon-btn" onClick={toggle} aria-label={theme === "dark" ? "Passer au thème clair" : "Passer au thème sombre"} title={theme === "dark" ? "Thème clair" : "Thème sombre"}>
            {theme === "dark" ? (
              <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><circle cx="9" cy="9" r="4" fill="currentColor" /><g stroke="currentColor" strokeWidth="1.8">{[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (<line key={a} x1="9" y1="1" x2="9" y2="3.2" transform={`rotate(${a} 9 9)`} />))}</g></svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><path d="M12.5 11.8A6 6 0 0 1 6.2 2.6a6.6 6.6 0 1 0 8.7 8.6 6 6 0 0 1-2.4.6z" fill="currentColor" /></svg>
            )}
          </button>
          <a className="icon-btn" href={REPO_URL} aria-label="Code source sur GitHub" title="Code source sur GitHub">
            <svg width="18" height="18" viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z" /></svg>
          </a>
        </div>
      </div>
    </header>
  );
}
