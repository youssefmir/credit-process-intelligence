import { useCallback, useMemo } from "react";

import EChart, { axisCommon, type OptionBuilder } from "../components/EChart";
import Figure from "../components/Figure";
import Reveal from "../components/Reveal";
import Section from "../components/Section";
import type { AllData } from "../lib/data";
import { eur, num, pct } from "../lib/format";

interface Band {
  band: string;
  cases: number;
  cancelled: number;
  cancel_rate: number | null;
  approval_rate: number | null;
}

export default function Abandon({ data }: { data: AllData }) {
  const ab = data.abandon;
  const stages = ab.by_stage as { stage: string; label: string; cancelled: number; share: number; median_days_from_submission: number | null }[];

  const stageBuild = useCallback<OptionBuilder>(
    (p) => ({
      grid: { left: 8, right: 70, top: 8, bottom: 8, containLabel: true },
      xAxis: { ...axisCommon(p), type: "value", axisLabel: { show: false }, splitLine: { show: false }, axisLine: { show: false } },
      yAxis: {
        ...axisCommon(p),
        type: "category",
        inverse: true,
        data: stages.map((s) => s.label),
        axisLine: { lineStyle: { color: p.ink } },
        axisLabel: { ...axisCommon(p).axisLabel, color: p.ink2, width: 170, overflow: "break" },
      },
      tooltip: { formatter: (it: { name: string; value: number }) => `<strong>${num(it.value)} annulations</strong><br/>${it.name}` },
      series: [
        {
          type: "bar",
          barWidth: 18,
          data: stages.map((s) => ({ value: s.cancelled, itemStyle: { color: p.red } })),
          label: { show: true, position: "right", color: p.ink, formatter: (it: { value: number }) => num(it.value) },
        },
      ],
    }),
    [stages],
  );

  const expiryBuild = useCallback<OptionBuilder>(
    (p) => {
      const hist = ab.after_offer.hist_days_since_last_offer as number[];
      return {
        grid: { left: 8, right: 16, top: 16, bottom: 8, containLabel: true },
        xAxis: {
          ...axisCommon(p),
          type: "category",
          data: hist.map((_, i) => i),
          axisLabel: { ...axisCommon(p).axisLabel, interval: 9, formatter: (v: string) => `${v} j` },
          splitLine: { show: false },
        },
        yAxis: { ...axisCommon(p), type: "value", splitNumber: 3 },
        tooltip: { formatter: (it: { name: string; value: number }) => `<strong>${num(it.value)} annulations</strong><br/>${it.name} à ${Number(it.name) + 1} jours après la dernière offre` },
        series: [
          {
            type: "bar",
            barCategoryGap: "12%",
            data: hist.map((v, i) => ({ value: v, itemStyle: { color: i >= 29 && i <= 31 ? p.red : p.ctx } })),
            markPoint: {
              symbol: "rect",
              symbolSize: 1,
              label: {
                show: true,
                color: p.ink,
                fontFamily: '"Archivo Variable"',
                fontWeight: 600,
                formatter: `Expiration de l'offre : ${pct(ab.after_offer.expiry_window_share)} des annulations`,
                position: "left",
                distance: 8,
              },
              itemStyle: { color: "transparent" },
              data: [{ coord: [29, Math.round(Math.max(...hist) * 0.72)] }],
            },
          },
        ],
      };
    },
    [ab.after_offer],
  );

  const rateBuild = (rows: Band[], highlightLast: boolean): OptionBuilder => (p) => ({
    grid: { left: 8, right: 16, top: 26, bottom: 8, containLabel: true },
    xAxis: { ...axisCommon(p), type: "category", data: rows.map((r) => r.band), splitLine: { show: false }, axisLine: { lineStyle: { color: p.ink } } },
    yAxis: { ...axisCommon(p), type: "value", max: 0.6, splitNumber: 3, axisLabel: { ...axisCommon(p).axisLabel, formatter: (v: number) => pct(v) } },
    tooltip: {
      formatter: (it: { dataIndex: number }) => {
        const r = rows[it.dataIndex];
        return `<strong>${pct(r.cancel_rate, 1)} annulées</strong><br/>${r.band} · ${num(r.cases)} dossiers`;
      },
    },
    series: [
      {
        type: "bar",
        barWidth: 22,
        data: rows.map((r, i) => ({
          value: r.cancel_rate,
          itemStyle: { color: highlightLast ? (i >= rows.length - 2 ? p.red : p.ctx) : r.band === "< 5 k€" ? p.red : p.ctx },
        })),
        label: { show: true, position: "top", color: p.ink, formatter: (it: { value: number }) => pct(it.value) },
      },
    ],
  });

  const delayRows = (ab.by_delay_to_offer as Band[]).filter((r) => r.cases >= 30);
  const amountRows = ab.by_amount_offered as Band[];
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const delayBuild = useMemo(() => rateBuild(delayRows, true), [ab]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const amountBuild = useMemo(() => rateBuild(amountRows, false), [ab]);
  const med = ab.median_amount_by_outcome;

  return (
    <Section
      id="abandons"
      num="06"
      kicker="Qui abandonne, quand, et pourquoi"
      title={
        <>
          {pct(ab.cancel_rate_after_offer)} des offres envoyées finissent annulées, dont{" "}
          {pct(ab.after_offer.expiry_window_share)} le jour où l'offre expire.
        </>
      }
      lede={
        <>
          {num(ab.cancelled)} dossiers sont annulés ({pct(ab.share_of_closed)} des dossiers clos). Le journal ne dit pas
          pourquoi ; il dit quand. Deux moments dominent : pendant la complétion, avant toute offre, et après l'envoi
          de l'offre, quand le client ne la renvoie pas.
        </>
      }
    >
      <div className="grid">
        <Reveal className="span-5">
          <Figure
            title="Étape à laquelle le dossier est annulé"
            table={{
              columns: ["Étape", "Annulations", "Part", "Délai médian depuis le dépôt"],
              rows: stages.map((s) => [s.label, num(s.cancelled), pct(s.share, 1), s.median_days_from_submission === null ? "—" : `${num(s.median_days_from_submission, 1)} j`]),
              numeric: [1, 2, 3],
            }}
          >
            <EChart build={stageBuild} height={210} label="Annulations par étape" />
          </Figure>
        </Reveal>
        <Reveal className="span-7" delay={0.06}>
          <Figure
            title="Jours entre la dernière offre et l'annulation"
            subtitle={`${num(ab.after_offer.cases)} dossiers annulés après l'envoi d'une offre.`}
          >
            <EChart build={expiryBuild} height={240} label="Distribution du délai entre dernière offre et annulation" />
          </Figure>
        </Reveal>
        <Reveal className="span-6">
          <Figure
            title="Plus l'offre tarde, plus l'abandon est fréquent"
            subtitle="Taux d'annulation selon le délai entre dépôt et première offre (dossiers ayant reçu une offre)."
            table={{
              columns: ["Délai avant offre", "Dossiers", "Annulés", "Taux"],
              rows: delayRows.map((r) => [r.band, num(r.cases), num(r.cancelled), pct(r.cancel_rate, 1)]),
              numeric: [1, 2, 3],
            }}
          >
            <EChart build={delayBuild} height={220} label="Taux d'annulation par délai avant la première offre" />
          </Figure>
        </Reveal>
        <Reveal className="span-6" delay={0.06}>
          <Figure
            title="Les petits montants abandonnent davantage"
            subtitle="Taux d'annulation selon le montant demandé (dossiers ayant reçu une offre)."
            table={{
              columns: ["Montant", "Dossiers", "Annulés", "Taux"],
              rows: amountRows.map((r) => [r.band, num(r.cases), num(r.cancelled), pct(r.cancel_rate, 1)]),
              numeric: [1, 2, 3],
            }}
          >
            <EChart build={amountBuild} height={220} label="Taux d'annulation par tranche de montant" />
          </Figure>
          <p className="small muted">
            Montant médian demandé : {eur(med.approved)} pour les prêts approuvés, {eur(med.cancelled)} pour les
            dossiers annulés, {eur(med.declined)} pour les refus.
          </p>
        </Reveal>
      </div>
    </Section>
  );
}
