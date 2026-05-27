import { useEffect, useState } from "react";

import { useInViewOnce, useReducedMotion } from "../lib/motion";

interface Props {
  value: number;
  format: (v: number) => string;
  duration?: number;
  className?: string;
}

/**
 * Chiffre qui s'incrémente une seule fois à l'apparition. La largeur finale est réservée
 * par un fantôme invisible : aucun saut de mise en page pendant l'animation.
 */
export default function CountUp({ value, format, duration = 600, className }: Props) {
  const { ref, seen } = useInViewOnce<HTMLSpanElement>("0px");
  const reduced = useReducedMotion();
  const [shown, setShown] = useState(reduced ? value : 0);

  useEffect(() => {
    if (!seen) return;
    if (reduced) {
      setShown(value);
      return;
    }
    let raf = 0;
    const start = performance.now();
    const step = (now: number) => {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - (1 - p) ** 3;
      setShown(value * eased);
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [seen, value, duration, reduced]);

  return (
    <span ref={ref} className={`countup ${className ?? ""}`}>
      <span className="countup-ghost" aria-hidden="true">
        {format(value)}
      </span>
      <span className="countup-live" aria-hidden="true">
        {format(shown)}
      </span>
      <span className="sr-only">{format(value)}</span>
    </span>
  );
}
