import { useCallback } from "react";

import EChart, { axisCommon, type OptionBuilder } from "../components/EChart";
import Figure from "../components/Figure";
import Reveal from "../components/Reveal";
import Section from "../components/Section";
import type { AllData } from "../lib/data";
import { num, pct } from "../lib/format";

export default function Rework({ data }: { data: AllData }) {
  const rw = data.rework;
  const inc = rw.incomplete;
  const mo = rw.multiple_offers;
  const fu = rw.offer_follow_ups;
  const annual = data.meta.window.annual_factor as number;

  const hoursBuild = useCallback<OptionBuilder>(
    (p) => {
      const rows = [
        { label: "Relances d'offres (autres)", value: fu.hours_annual - mo.hours_after_second_offer_annual, color: p.ctx },
        { label: "Relances après une 2e offre", value: mo.hours_after_second_offer_annual, color: p.ctx },
        { label: "Re-validations après pièces", value: Math.round(inc.revalidation_hours * annual), color: p.yellow },
        { label: "Appels pour pièces manquantes", value: Math.round(inc.call_hours * annual), color: p.yellow },
      ];
      return {
        grid: { left: 8, right: 70, top: 8, bottom: 8, containLabel: true },
        xAxis: { ...axisCommon(p), type: "value", axisLabel: { show: false }, splitLine: { show: false }, axisLine: { show: false } },
        yAxis: { ...axisCommon(p), type: "category", data: rows.map((r) => r.label), axisLine: { lineStyle: { color: p.ink } }, axisLabel: { ...axisCommon(p).axisLabel, color: p.ink2 } },
        tooltip: { formatter: (it: { name: string; value: number }) => `<strong>${num(it.value)} h par an</strong><br/>${it.name}` },
        series: [
          {
            type: "bar",
            barWidth: 18,
            data: rows.map((r) => ({ value: r.value, itemStyle: { color: r.color } })),
            label: { show: true, position: "right", color: p.ink, formatter: (it: { value: number }) => `${num(it.value)} h` },
          },
        ],
      };
    },
    [fu, mo, inc, annual],
  );

  const delayBuild = useCallback<OptionBuilder>(
    (p) => ({
      grid: { left: 8, right: 16, top: 24, bottom: 8, containLabel: true },
      xAxis: {
        ...axisCommon(p),
        type: "category",
        data: (rw.loop_delay_hist as number[]).map((_, i) => i),
        axisLabel: { ...axisCommon(p).axisLabel, interval: 4, formatter: (v: string) => `${v} j` },
        splitLine: { show: false },
      },
      yAxis: { ...axisCommon(p), type: "value", splitNumber: 3 },
      tooltip: { formatter: (it: { name: string; value: number }) => `<strong>${num(it.value)} dossiers</strong><br/>boucle de ${it.name} à ${Number(it.name) + 1} jours` },
      series: [
        {
          type: "bar",
          data: rw.loop_delay_hist,
          barCategoryGap: "14%",
          itemStyle: { color: p.yellow },
          markLine: {
            symbol: "none",
            silent: true,
            lineStyle: { color: p.ink, width: 1.5, type: "solid" },
            label: { show: true, formatter: `médiane ${num(inc.median_loop_delay_d, 1)} j`, color: p.ink, position: "end" },
            data: [{ xAxis: Math.floor(inc.median_loop_delay_d) }],
          },
        },
      ],
    }),
    [rw.loop_delay_hist, inc.median_loop_delay_d],
  );

  const callsBuild = useCallback<OptionBuilder>(
    (p) => {
      const rows = [
        { key: "approved", label: "Approuvées" },
        { key: "declined", label: "Refusées" },
        { key: "cancelled", label: "Annulées" },
      ];
      return {
        grid: { left: 8, right: 60, top: 8, bottom: 8, containLabel: true },
        xAxis: { ...axisCommon(p), type: "value", axisLabel: { show: false }, splitLine: { show: false }, axisLine: { show: false } },
        yAxis: { ...axisCommon(p), type: "category", data: rows.map((r) => r.label), axisLine: { lineStyle: { color: p.ink } }, axisLabel: { ...axisCommon(p).axisLabel, color: p.ink2 } },
        tooltip: { formatter: (it: { name: string; value: number }) => `<strong>${num(it.value, 1)} appels</strong> en moyenne<br/>dossiers ${it.name.toLowerCase()}` },
        series: [
          {
            type: "bar",
            barWidth: 18,
            data: rows.map((r) => ({ value: fu.mean_calls_by_outcome[r.key], itemStyle: { color: r.key === "cancelled" ? p.red : p.ctx } })),
            label: { show: true, position: "right", color: p.ink, formatter: (it: { value: number }) => `${num(it.value, 1)}` },
          },
        ],
      };
    },
    [fu],
  );

  return (
    <Section
      id="allers-retours"
      num="05"
      kicker="Le coût des allers-retours"
      title={
        <>
          {pct(inc.share_of_validated)} des dossiers validés repartent chercher des pièces : {num(rw.total_rework_hours_annual)}{" "}
          heures de relances et de reprises par an.
        </>
      }
      lede={
        <>
          Trois boucles de reprise ressortent du journal. Elles ne pèsent que quelques milliers d'heures, mais elles
          allongent le délai et précèdent une partie des abandons. Heures annualisées (× {num(annual, 2)}, soit 365
          jours rapportés aux {num(data.meta.window.submission_days, 0)} jours de dépôts observés).
        </>
      }
    >
      <div className="grid rework-cols">
        <Reveal className="span-4 rework-col">
          <p className="kicker">Boucle « dossier incomplet »</p>
          <p className="figure-number sm">{num(inc.cases)}</p>
          <p className="label">dossiers ({pct(inc.share_of_approved)} des prêts approuvés)</p>
          <ul className="facts">
            <li>{num(inc.calls)} appels, {num(inc.median_calls_per_case)} en médiane par dossier</li>
            <li>{num(inc.call_hours)} h d'appels et {num(inc.revalidation_hours)} h de re-validation observées</li>
            <li>
              Délai médian des prêts approuvés : {num(inc.median_lead_time_approved_with_d, 1)} j avec la boucle,{" "}
              {num(inc.median_lead_time_approved_without_d, 1)} j sans
            </li>
          </ul>
        </Reveal>
        <Reveal className="span-4 rework-col" delay={0.06}>
          <p className="kicker">Offres multiples</p>
          <p className="figure-number sm">{pct(mo.share_of_offered)}</p>
          <p className="label">des dossiers ayant reçu une offre en reçoivent plusieurs</p>
          <ul className="facts">
            <li>{num(mo.extra_offers)} offres supplémentaires créées</li>
            <li>{num(mo.median_span_d, 1)} j médians entre la première et la dernière offre</li>
            <li>{num(mo.calls_after_second_offer)} appels de relance après une 2e offre</li>
          </ul>
        </Reveal>
        <Reveal className="span-4 rework-col" delay={0.12}>
          <p className="kicker">Relances d'offres</p>
          <p className="figure-number sm">{num(fu.calls)}</p>
          <p className="label">appels pour faire revenir {num(fu.cases)} offres</p>
          <ul className="facts">
            <li>{pct(fu.share_hours_on_cancelled)} de ces heures sont consacrées à des dossiers finalement annulés</li>
            <li>Retour médian de l'offre signée : {num(fu.median_return_d, 1)} j (P90 : {num(fu.p90_return_d, 1)} j)</li>
          </ul>
        </Reveal>

        <Reveal className="span-6">
          <Figure
            title="Heures de reprise par an"
            subtitle="En jaune : la boucle « dossier incomplet », cible du contrôle de complétude."
            table={{
              columns: ["Poste", "Heures par an"],
              rows: [
                ["Appels pour pièces manquantes", num(Math.round(inc.call_hours * annual))],
                ["Re-validations après pièces", num(Math.round(inc.revalidation_hours * annual))],
                ["Relances après une 2e offre", num(mo.hours_after_second_offer_annual)],
                ["Relances d'offres (autres)", num(fu.hours_annual - mo.hours_after_second_offer_annual)],
              ],
              numeric: [1],
            }}
          >
            <EChart build={hoursBuild} height={220} label="Heures annuelles de reprise par poste" />
          </Figure>
        </Reveal>
        <Reveal className="span-6" delay={0.06}>
          <Figure title="Durée d'une boucle « dossier incomplet »" subtitle="De la demande de pièces à la reprise de la validation.">
            <EChart build={delayBuild} height={220} label="Distribution de la durée des boucles dossier incomplet" />
          </Figure>
        </Reveal>
        <Reveal className="span-6">
          <Figure title="Appels de relance d'offre par dossier, selon l'issue" subtitle="Moyenne par dossier ayant reçu une offre.">
            <EChart build={callsBuild} height={170} label="Appels de relance moyens par issue" />
          </Figure>
        </Reveal>
        <Reveal className="span-6 aside-col" delay={0.06}>
          <p className="note">
            Les dossiers annulés reçoivent en moyenne {num(fu.mean_calls_by_outcome.cancelled, 1)} appels de relance,
            contre {num(fu.mean_calls_by_outcome.approved, 1)} pour les dossiers approuvés : l'effort de relance se
            concentre sur les clients qui ne reviendront pas. Savoir les reconnaître plus tôt aurait de la valeur ;
            la section 07 teste si c'est possible.
          </p>
        </Reveal>
      </div>
    </Section>
  );
}
