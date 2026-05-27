import { motion, useReducedMotion } from "motion/react";

import { num, pct } from "../lib/format";

export interface Segment {
  key: string;
  label: string;
  value: number;
  color: string;
  /** Couleur du texte imprimé dans le bloc (blanc ou encre selon la luminance du fond). */
  textColor?: string;
}

interface Props {
  segments: Segment[];
  ariaLabel: string;
  unit?: (v: number, share: number) => string;
}

/** Barre segmentée haute : une partie par bloc, part imprimée quand elle tient, légende des noms. */
export default function SegmentedBar({ segments, ariaLabel, unit }: Props) {
  const reduced = useReducedMotion();
  const total = segments.reduce((a, s) => a + s.value, 0) || 1;
  return (
    <div className="segbar">
      <div className="segbar-track" role="img" aria-label={ariaLabel}>
        {segments.map((s, i) => {
          const share = s.value / total;
          return (
            <motion.div
              key={s.key}
              className="segbar-part"
              style={{ flexGrow: share, background: s.color, color: s.textColor ?? "#fff", transformOrigin: "left" }}
              title={`${s.label} : ${num(s.value)} (${pct(share, 1)})`}
              initial={reduced ? false : { scaleX: 0, opacity: 0 }}
              whileInView={{ scaleX: 1, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: reduced ? 0 : 0.06 * i }}
            >
              {share >= 0.07 && <span>{unit ? unit(s.value, share) : pct(share)}</span>}
            </motion.div>
          );
        })}
      </div>
      <ul className="segbar-legend">
        {segments.map((s) => (
          <li key={s.key}>
            <span className="swatch block" style={{ background: s.color }} />
            {s.label} <span className="muted num">{unit ? unit(s.value, s.value / total) : num(s.value)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
