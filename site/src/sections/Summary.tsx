import CountUp from "../components/CountUp";
import Reveal from "../components/Reveal";
import Section from "../components/Section";
import type { AllData, OppKey } from "../lib/data";
import { hoursMinutes, keur, num, pct } from "../lib/format";

const VERDICT: Record<OppKey, { tag: string; cls: string; text: string }> = {
  completeness: { tag: "Lancer", cls: "ok", text: "Seule opportunité rentable dans la majorité des scénarios." },
  prioritization: { tag: "Piloter en A/B", cls: "neutral", text: "Rentabilité incertaine, portée par le taux de récupération, pas par le modèle." },
  preanalysis: { tag: "Différer", cls: "ko", text: "Gain de productivité trop faible à ce volume ; à réévaluer avec un socle mutualisé." },
};

export default function Summary({ data }: { data: AllData }) {
  const s = data.summary;
  const time = data.time.phases.approved_summary;
  const rw = data.rework;
  const ab = data.abandon;
  const bc = data.business_case;
  const order: OppKey[] = ["completeness", "prioritization", "preanalysis"];
  return (
    <Section
      id="synthese"
      num="01"
      kicker="Synthèse exécutive"
      title={<>Le temps se perd en attente ; la valeur se perd en abandons.</>}
      lede={
        <>
          Une institution de crédit à la consommation reçoit environ {num(s.annualized_applications)} demandes par an
          (volume annualisé à partir de 5 mois observés). {pct(s.approved_share)} seulement aboutissent à un prêt,{" "}
          {pct(s.declined_share)} sont refusées et {pct(s.cancelled_share)} abandonnées en route. La question posée :
          où l'IA crée-t-elle de la valeur, combien, et à quelles conditions ?
        </>
      }
    >
      <div className="grid findings">
        <Reveal className="span-4 finding">
          <p className="finding-num">1</p>
          <p className="figure-number">
            <CountUp value={time.flow_efficiency_aggregate * 100} format={(v) => `${num(v, 2)}\u00a0%`} />
          </p>
          <h3 className="h3">d'efficacité de flux</h3>
          <p className="muted">
            Un prêt approuvé demande {hoursMinutes(time.mean_work_h)} de travail effectif pour{" "}
            {num(time.mean_lead_time_d, 1)} jours de délai moyen. Le reste est de l'attente : le client, puis la file
            de validation.
          </p>
          <a href="#temps">Où se perd le temps</a>
        </Reveal>
        <Reveal className="span-4 finding" delay={0.08}>
          <p className="finding-num">2</p>
          <p className="figure-number">
            <CountUp value={rw.incomplete.share_of_validated * 100} format={(v) => `${num(v)}\u00a0%`} />
          </p>
          <h3 className="h3">des dossiers validés repartent chercher des pièces</h3>
          <p className="muted">
            Chaque boucle « dossier incomplet » coûte en médiane {num(rw.incomplete.median_calls_per_case)} appels et{" "}
            {num(rw.incomplete.median_loop_delay_d, 1)} jours ; soit {num(rw.incomplete.loop_hours_annual)} heures par
            an de reprise.
          </p>
          <a href="#allers-retours">Le coût des allers-retours</a>
        </Reveal>
        <Reveal className="span-4 finding" delay={0.16}>
          <p className="finding-num">3</p>
          <p className="figure-number">
            <CountUp value={ab.cancel_rate_after_offer * 100} format={(v) => `${num(v)}\u00a0%`} />
          </p>
          <h3 className="h3">des offres envoyées finissent annulées</h3>
          <p className="muted">
            {pct(ab.after_offer.expiry_window_share)} de ces annulations tombent à l'expiration des 30 jours : le
            client n'a jamais renvoyé l'offre. Les traces du processus ne permettent pas de prévoir qui abandonnera
            (ROC-AUC {num(s.model_roc_auc, 2)}).
          </p>
          <a href="#abandons">Qui abandonne</a>
        </Reveal>
      </div>

      <Reveal className="reco">
        <h3 className="h3">Trois opportunités IA évaluées, une seule à lancer maintenant</h3>
        <div className="table-wrap">
          <table className="data reco-table">
            <thead>
              <tr>
                <th scope="col">Opportunité</th>
                <th scope="col">Verdict</th>
                <th scope="col" className="r">VAN 3 ans (médiane)</th>
                <th scope="col" className="r">P(VAN &gt; 0)</th>
              </tr>
            </thead>
            <tbody>
              {order.map((k) => {
                const o = bc.opportunities[k];
                return (
                  <tr key={k}>
                    <td>
                      <strong>{o.title}</strong>
                      <br />
                      <span className="muted small">{VERDICT[k].text}</span>
                    </td>
                    <td>
                      <span className={`tag ${VERDICT[k].cls}`}>{VERDICT[k].tag}</span>
                    </td>
                    <td className="r">
                      <strong>{keur(o.monte_carlo.npv.p50, 0, true)}</strong>
                      <br />
                      <span className="muted small">
                        {keur(o.monte_carlo.npv.p10, 0, true)} à {keur(o.monte_carlo.npv.p90, 0, true)}
                      </span>
                    </td>
                    <td className="r">{pct(o.monte_carlo.prob_npv_positive)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="source">
          VAN sur 36 mois, Monte Carlo ({num(bc.opportunities.completeness.monte_carlo.iterations)} tirages) sur des
          hypothèses explicites ; fourchette P10 à P90. Détail et curseurs dans la section 08.
        </p>
      </Reveal>
    </Section>
  );
}
