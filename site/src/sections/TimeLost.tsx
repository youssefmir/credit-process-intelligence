import { motion, useReducedMotion } from "motion/react";
import { useCallback, useMemo } from "react";

import EChart, { axisCommon, type OptionBuilder } from "../components/EChart";
import Figure from "../components/Figure";
import Reveal from "../components/Reveal";
import Section from "../components/Section";
import SegmentedBar from "../components/SegmentedBar";
import type { AllData } from "../lib/data";
import { hoursMinutes, num, pct } from "../lib/format";
import { usePalette } from "../lib/theme";

interface Activity {
  activity: string;
  label: string;
  sessions: number;
  cases: number;
  work_h: number;
  median_session_min: number;
  median_wait_h: number;
  p90_wait_h: number;
  sessions_per_case: number;
  median_gap_h: number | null;
}

function Waffle({ hours, workHours }: { hours: number; workHours: number }) {
  const reduced = useReducedMotion();
  const n = Math.round(hours);
  const full = Math.floor(workHours);
  const frac = workHours - full;
  const cells = Array.from({ length: n }, (_, i) => i);
  return (
    <div className="waffle" role="img" aria-label={`${num(n)} heures de délai moyen, dont ${hoursMinutes(workHours)} de travail effectif`}>
      {cells.map((i) => {
        const work = i < full ? 1 : i === full ? frac : 0;
        return (
          <motion.span
            key={i}
            className="waffle-cell"
            initial={reduced ? false : { opacity: 0, scale: 0.6 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true, margin: "0px 0px -10% 0px" }}
            transition={{ duration: 0.25, delay: reduced ? 0 : Math.floor(i / 20) * 0.025 }}
          >
            {work > 0 && <span className="waffle-work" style={{ width: `${work * 100}%` }} />}
          </motion.span>
        );
      })}
    </div>
  );
}

export default function TimeLost({ data }: { data: AllData }) {
  const palette = usePalette();
  const t = data.time;
  const appr = t.phases.approved as { phase: string; label: string; mean_elapsed_d: number; mean_work_h: number; cases: number }[];
  const sum = t.phases.approved_summary;
  const acts = (t.activities as Activity[]).filter((a) => a.activity !== "W_Beoordelen fraude");
  const lead = t.lead_times;
  const res = t.resources;
  const byPhase = Object.fromEntries(appr.map((p) => [p.phase, p]));

  const leadBuild = useCallback<OptionBuilder>(
    (p, { width }) => {
      const outcomes = [
        { key: "approved", label: "Approuvées", color: p.green },
        { key: "cancelled", label: "Annulées", color: p.red },
        { key: "declined", label: "Refusées", color: p.grey },
      ];
      const narrow = width < 640;
      const grids = outcomes.map((_, i) =>
        narrow
          ? { left: 44, right: 12, top: 28 + i * 150, height: 100 }
          : { left: `${4 + i * 33}%`, width: "27%", top: 34, height: 170 },
      );
      return {
        grid: grids,
        xAxis: outcomes.map((_, i) => ({
          ...axisCommon(p),
          gridIndex: i,
          type: "category",
          data: lead.bins_days.map((d: number) => d),
          axisLabel: { ...axisCommon(p).axisLabel, interval: 9, formatter: (v: string) => `${v} j` },
          splitLine: { show: false },
        })),
        yAxis: outcomes.map((_, i) => ({
          ...axisCommon(p),
          gridIndex: i,
          type: "value",
          splitNumber: 3,
          axisLabel: { ...axisCommon(p).axisLabel, formatter: (v: number) => num(v) },
        })),
        graphic: outcomes.map((o, i) => ({
          type: "text",
          left: narrow ? 44 : `${4 + i * 33}%`,
          top: narrow ? 8 + i * 150 : 8,
          style: {
            text: `${o.label} — médiane ${num(lead.by_outcome[o.key].quantiles.p50, 1)} j`,
            fill: p.ink,
            font: '600 13px "Archivo Variable", sans-serif',
          },
        })),
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "line", lineStyle: { color: p.ink, width: 1 } },
          formatter: (items: { axisValue: string; value: number; seriesName: string }[]) => {
            const it = items[0];
            return `<strong>${num(it.value)} dossiers</strong><br/>${it.seriesName}, ${it.axisValue} à ${Number(it.axisValue) + 1} jours`;
          },
        },
        series: outcomes.map((o, i) => ({
          name: o.label,
          type: "bar",
          xAxisIndex: i,
          yAxisIndex: i,
          data: lead.by_outcome[o.key].hist,
          itemStyle: { color: o.color },
          barCategoryGap: "12%",
          markLine: {
            symbol: "none",
            silent: true,
            lineStyle: { color: p.ink, width: 1.5, type: "solid" },
            label: { show: false },
            data: [{ xAxis: Math.min(Math.floor(lead.by_outcome[o.key].quantiles.p50), 59) }],
          },
        })),
      };
    },
    [lead],
  );

  const barBuild = (field: "median_wait_h" | "median_session_min", unit: string, highlight: string): OptionBuilder =>
    (p) => {
      const sorted = [...acts].sort((a, b) => a[field] - b[field]);
      return {
        grid: { left: 8, right: 64, top: 8, bottom: 8, containLabel: true },
        xAxis: { ...axisCommon(p), type: "value", splitNumber: 3, axisLabel: { show: false }, splitLine: { show: false }, axisLine: { show: false } },
        yAxis: {
          ...axisCommon(p),
          type: "category",
          data: sorted.map((a) => a.label),
          axisLine: { lineStyle: { color: p.ink, width: 1 } },
          axisLabel: { ...axisCommon(p).axisLabel, color: p.ink2, width: 150, overflow: "break" },
        },
        tooltip: { trigger: "item", formatter: (it: { name: string; value: number }) => `<strong>${num(it.value, 1)} ${unit}</strong><br/>${it.name}` },
        series: [
          {
            type: "bar",
            barWidth: 16,
            data: sorted.map((a) => ({ value: a[field], itemStyle: { color: a.activity === highlight ? p.blue : p.ctx } })),
            label: { show: true, position: "right", color: p.ink, formatter: (it: { value: number }) => `${num(it.value, 1)} ${unit}` },
          },
        ],
      };
    };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const waitBuild = useMemo(() => barBuild("median_wait_h", "h", "W_Valideren aanvraag"), [t.activities]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const workBuild = useMemo(() => barBuild("median_session_min", "min", "W_Valideren aanvraag"), [t.activities]);

  const weeklyBuild = useCallback<OptionBuilder>(
    (p) => {
      const weeks = t.weekly.weeks as string[];
      const series = t.weekly.series as Record<string, number[]>;
      const total = weeks.map((_, i) => Object.values(series).reduce((a, s) => a + s[i], 0));
      const rework = weeks.map((_, i) => series["W_Nabellen incomplete dossiers"][i] + series["W_Nabellen offertes"][i]);
      return {
        grid: { left: 8, right: 110, top: 16, bottom: 8, containLabel: true },
        xAxis: {
          ...axisCommon(p),
          type: "category",
          data: weeks,
          boundaryGap: false,
          axisLabel: {
            ...axisCommon(p).axisLabel,
            formatter: (v: string) => new Date(v).toLocaleDateString("fr-FR", { day: "numeric", month: "short" }),
            interval: 3,
          },
        },
        yAxis: { ...axisCommon(p), type: "value", splitNumber: 4, axisLabel: { ...axisCommon(p).axisLabel, formatter: (v: number) => `${num(v)} h` } },
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "line", lineStyle: { color: p.ink, width: 1 } },
          formatter: (items: { axisValue: string; value: number; seriesName: string }[]) =>
            `${new Date(items[0].axisValue).toLocaleDateString("fr-FR", { day: "numeric", month: "long" })}<br/>` +
            items.map((it) => `<strong>${num(it.value)} h</strong> ${it.seriesName}`).join("<br/>"),
        },
        series: [
          {
            name: "toutes tâches",
            type: "line",
            data: total.map((v) => Math.round(v)),
            showSymbol: false,
            lineStyle: { color: p.ink, width: 2 },
            itemStyle: { color: p.ink },
            endLabel: { show: true, formatter: "Toutes tâches", color: p.ink, fontFamily: '"Archivo Variable"' },
          },
          {
            name: "dont relances",
            type: "line",
            data: rework.map((v) => Math.round(v)),
            showSymbol: false,
            lineStyle: { color: p.yellow, width: 2 },
            itemStyle: { color: p.yellow },
            areaStyle: { color: p.yellow, opacity: 0.12 },
            endLabel: { show: true, formatter: "dont relances", color: p.ink, fontFamily: '"Archivo Variable"' },
          },
        ],
      };
    },
    [t.weekly],
  );

  const heatBuild = useCallback<OptionBuilder>(
    (p) => {
      const hm = t.heatmap as { days: string[]; hours: number[]; values: number[][] };
      const points: [number, number, number][] = [];
      hm.values.forEach((row, d) => row.forEach((v, h) => points.push([h, d, v])));
      const max = Math.max(...points.map((x) => x[2]));
      return {
        grid: { left: 8, right: 8, top: 8, bottom: 40, containLabel: true },
        xAxis: { ...axisCommon(p), type: "category", data: hm.hours.map((h) => `${h} h`), splitArea: { show: false }, axisLabel: { ...axisCommon(p).axisLabel, interval: 2 } },
        yAxis: { ...axisCommon(p), type: "category", data: hm.days, inverse: true, axisLine: { show: false } },
        visualMap: {
          min: 0,
          max,
          show: true,
          orient: "horizontal",
          left: "center",
          bottom: 0,
          itemWidth: 10,
          itemHeight: 140,
          text: ["plus de sessions", "aucune"],
          textStyle: { color: p.muted, fontFamily: '"Archivo Variable"' },
          inRange: { color: [p.bg, ...p.seq.slice(1)] },
          calculable: false,
        },
        tooltip: {
          formatter: (it: { value: [number, number, number] }) =>
            `<strong>${num(it.value[2])} sessions</strong><br/>${hm.days[it.value[1]]}, ${it.value[0]} h – ${it.value[0] + 1} h`,
        },
        series: [{ type: "heatmap", data: points, itemStyle: { borderColor: p.bg, borderWidth: 2 } }],
      };
    },
    [t.heatmap],
  );

  const bottlenecks = (t.bottlenecks as { source_label: string; target_label: string; count: number; median_h: number; share_of_time: number }[]).slice(0, 6);
  const phaseSegs = appr.map((ph, i) => ({
    key: ph.phase,
    label: ph.label,
    value: ph.mean_elapsed_d,
    color: palette.ord[i],
    textColor: i < 2 ? palette.ink : "#ffffff",
  }));

  return (
    <Section
      id="temps"
      num="04"
      kicker="Où se perd le temps"
      title={
        <>
          Sur {num(sum.mean_lead_time_d, 1)} jours de délai moyen, le client en tient {num(byPhase.customer.mean_elapsed_d, 1)}{" "}
          et la file de validation {num(byPhase.validation.mean_elapsed_d, 1)}.
        </>
      }
      lede={
        <>
          Les tâches humaines ont un cycle de vie (planifiée, démarrée, terminée), ce qui sépare le temps de travail
          effectif du temps d'attente. L'efficacité de flux (travail ÷ délai total) d'un prêt approuvé est de{" "}
          {pct(sum.flow_efficiency_aggregate, 2)}.
        </>
      }
    >
      <div className="grid">
        <Reveal className="span-7">
          <Figure
            title="Le délai moyen d'un prêt approuvé, heure par heure"
            subtitle={`Chaque carré représente une heure ; en couleur, le travail effectif (${hoursMinutes(sum.mean_work_h)}).`}
            table={{
              columns: ["Phase", "Délai moyen", "Travail moyen"],
              rows: appr.map((ph) => [ph.label, `${num(ph.mean_elapsed_d, 2)} j`, hoursMinutes(ph.mean_work_h)]),
              numeric: [1, 2],
            }}
          >
            <Waffle hours={sum.mean_lead_time_d * 24} workHours={sum.mean_work_h} />
          </Figure>
        </Reveal>
        <Reveal className="span-5" delay={0.06}>
          <Figure title="Décomposition par phase (moyenne, jours)" subtitle="Dossiers approuvés ; phases dans l'ordre du parcours.">
            <SegmentedBar segments={phaseSegs} ariaLabel={appr.map((p) => `${p.label} ${num(p.mean_elapsed_d, 1)} jours`).join(", ")} unit={(v) => `${num(v, 1)} j`} />
          </Figure>
          <ul className="phase-notes">
            {appr.map((ph) => (
              <li key={ph.phase}>
                <strong>{ph.label}</strong> : {num(ph.mean_elapsed_d, 1)} j d'attente pour {hoursMinutes(ph.mean_work_h)} de travail
              </li>
            ))}
          </ul>
          <div className="stat resources">
            <p className="figure-number sm">{pct(res.top10_share)}</p>
            <p className="label">
              des heures de travail sont réalisées par 10 des {num(res.resources_with_work)} collaborateurs observés
              (identifiants pseudonymisés, lecture agrégée uniquement).
            </p>
          </div>
        </Reveal>

        <Reveal className="span-12">
          <Figure
            title="Délai jusqu'à l'issue, par issue"
            subtitle="Nombre de dossiers par jour de délai ; trait vertical : médiane."
            table={{
              columns: ["Issue", "P25", "Médiane", "P75", "P90"],
              rows: (["approved", "cancelled", "declined"] as const).map((k) => [
                { approved: "Approuvées", cancelled: "Annulées", declined: "Refusées" }[k],
                `${num(lead.by_outcome[k].quantiles.p25, 1)} j`,
                `${num(lead.by_outcome[k].quantiles.p50, 1)} j`,
                `${num(lead.by_outcome[k].quantiles.p75, 1)} j`,
                `${num(lead.by_outcome[k].quantiles.p90, 1)} j`,
              ]),
              numeric: [1, 2, 3, 4],
            }}
          >
            <EChart build={leadBuild} height={260} label="Histogrammes des délais par issue" />
          </Figure>
          <p className="small muted">
            {pct(lead.by_outcome.declined.within_1h_share)} des refus tombent en moins d'une heure (pré-contrôle
            automatique) ; les annulations montrent un pic vers 30 jours, l'expiration de l'offre.
          </p>
        </Reveal>

        <Reveal className="span-6">
          <Figure
            title="Attente médiane en file avant traitement"
            subtitle="De la planification d'une tâche à son premier démarrage."
            table={{
              columns: ["Tâche", "Attente médiane", "P90"],
              rows: acts.map((a) => [a.label, `${num(a.median_wait_h, 1)} h`, `${num(a.p90_wait_h, 0)} h`]),
              numeric: [1, 2],
            }}
          >
            <EChart build={waitBuild} height={230} label="Attente médiane en file par tâche" />
          </Figure>
        </Reveal>
        <Reveal className="span-6" delay={0.06}>
          <Figure
            title="Travail médian par session"
            subtitle="Durée d'une session de travail (appel, contrôle), après nettoyage."
            table={{
              columns: ["Tâche", "Session médiane", "Sessions par dossier", "Heures observées"],
              rows: acts.map((a) => [a.label, `${num(a.median_session_min, 1)} min`, num(a.sessions_per_case, 1), num(a.work_h)]),
              numeric: [1, 2, 3],
            }}
          >
            <EChart build={workBuild} height={230} label="Travail médian par session et par tâche" />
          </Figure>
        </Reveal>

        <Reveal className="span-7">
          <Figure
            title="Heures de travail par semaine"
            subtitle="Toutes tâches, dont relances (dossiers incomplets et offres). Première et dernières semaines incomplètes (démarrage et fin de l'extraction)."
            table={{
              columns: ["Semaine du", "Heures"],
              rows: (t.weekly.weeks as string[]).map((w: string, i: number) => [
                new Date(w).toLocaleDateString("fr-FR"),
                num(Object.values(t.weekly.series as Record<string, number[]>).reduce((a, s) => a + s[i], 0)),
              ]),
              numeric: [1],
            }}
          >
            <EChart build={weeklyBuild} height={260} label="Heures de travail par semaine" />
          </Figure>
        </Reveal>
        <Reveal className="span-5" delay={0.06}>
          <Figure title="Quand travaille-t-on ?" subtitle="Sessions de travail par jour et heure de début.">
            <EChart build={heatBuild} height={260} label="Carte de chaleur des sessions par jour et heure" />
          </Figure>
        </Reveal>

        <Reveal className="span-12">
          <h3 className="h3">Où s'accumule le temps entre deux jalons</h3>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th scope="col">Transition</th>
                  <th scope="col" className="r">Passages</th>
                  <th scope="col" className="r">Durée médiane</th>
                  <th scope="col" className="r">Part du temps cumulé</th>
                </tr>
              </thead>
              <tbody>
                {bottlenecks.map((b) => (
                  <tr key={`${b.source_label}-${b.target_label}`}>
                    <td>
                      {b.source_label} → {b.target_label}
                    </td>
                    <td className="r">{num(b.count)}</td>
                    <td className="r">{b.median_h < 48 ? `${num(b.median_h, 1)} h` : `${num(b.median_h / 24, 1)} j`}</td>
                    <td className="r">{pct(b.share_of_time)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="source">Temps cumulé = nombre de passages × durée moyenne, sur la vue des jalons.</p>
        </Reveal>
      </div>
    </Section>
  );
}
