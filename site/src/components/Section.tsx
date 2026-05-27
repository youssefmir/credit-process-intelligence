import type { ReactNode } from "react";

import Reveal from "./Reveal";

interface Props {
  id: string;
  num: string;
  kicker: string;
  title: ReactNode;
  lede?: ReactNode;
  children: ReactNode;
}

/** Section numérotée : filet épais, numéro, titre qui énonce le constat chiffré. */
export default function Section({ id, num, kicker, title, lede, children }: Props) {
  return (
    <section id={id} className="section" aria-labelledby={`${id}-title`}>
      <div className="wrap">
        <Reveal className="section-head">
          <div className="section-num">
            <span>{num} —</span>
            <span>{kicker}</span>
          </div>
          <h2 id={`${id}-title`} className="h2">
            {title}
          </h2>
          {lede && <p className="lede section-lede">{lede}</p>}
        </Reveal>
        {children}
      </div>
    </section>
  );
}
