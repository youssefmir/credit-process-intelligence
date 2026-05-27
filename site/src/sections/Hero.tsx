import { motion, useReducedMotion } from "motion/react";

import CountUp from "../components/CountUp";
import NetworkReplay from "../components/NetworkReplay";
import { REPO_URL } from "../content/sections";
import type { AllData } from "../lib/data";
import { hoursMinutes, num, pct } from "../lib/format";

const ease = [0.16, 1, 0.3, 1] as const;

export default function Hero({ data }: { data: AllData }) {
  const s = data.summary;
  const reduced = useReducedMotion();
  const item = (i: number) =>
    reduced
      ? {}
      : {
          initial: { opacity: 0, y: 16 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.55, ease, delay: 0.08 * i },
        };
  const waiting = s.waiting_share_approved as number;
  return (
    <section className="hero" id="top" aria-labelledby="hero-title">
      <div className="wrap">
        <motion.p className="kicker" {...item(0)}>
          Étude de cas · Process mining et IA appliqués au crédit à la consommation
        </motion.p>
        <motion.h1 id="hero-title" className="display hero-title" {...item(1)}>
          Un dossier approuvé passe {pct(waiting, 1)} de son délai à attendre.
        </motion.h1>
      </div>
      <div className="wrap grid hero-grid">
        <div className="hero-text">
          <motion.p className="lede hero-lede" {...item(2)}>
            {num(s.cases)} demandes de crédit réelles d'une banque néerlandaise, rejouées pas à pas : où le temps se
            perd, ce que coûtent les allers-retours, et où l'IA crée réellement de la valeur, chiffrée et conforme à
            l'AI Act.
          </motion.p>
          <motion.dl className="hero-stats" {...item(3)}>
            <div className="stat">
              <dt className="sr-only">Délai médian d'un prêt approuvé</dt>
              <dd className="figure-number sm">
                <CountUp value={s.median_lead_time_approved_d} format={(v) => `${num(v, 1)}\u00a0j`} />
              </dd>
              <dd className="label">délai médian, du dépôt à l'approbation</dd>
            </div>
            <div className="stat">
              <dt className="sr-only">Travail effectif moyen par prêt approuvé</dt>
              <dd className="figure-number sm">
                <CountUp value={s.mean_work_approved_h} format={hoursMinutes} />
              </dd>
              <dd className="label">de travail effectif par dossier approuvé</dd>
            </div>
            <div className="stat">
              <dt className="sr-only">Part des offres envoyées finalement annulées</dt>
              <dd className="figure-number sm">
                <CountUp value={s.cancel_rate_after_offer * 100} format={(v) => `${num(v)}\u00a0%`} />
              </dd>
              <dd className="label">des offres envoyées finissent annulées</dd>
            </div>
          </motion.dl>
          <motion.div className="hero-cta" {...item(4)}>
            <a className="btn primary" href="#synthese">
              Lire l'étude
            </a>
            <a className="btn" href={REPO_URL}>
              Code et documents
            </a>
          </motion.div>
        </div>
        <motion.div
          className="hero-visual"
          {...(reduced ? {} : { initial: { opacity: 0 }, animate: { opacity: 1 }, transition: { duration: 0.6, ease, delay: 0.25 } })}
        >
          <NetworkReplay />
        </motion.div>
      </div>
    </section>
  );
}
