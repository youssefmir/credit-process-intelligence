import { useState } from "react";

import Reveal from "../components/Reveal";
import Section from "../components/Section";
import { docUrl, REPO_URL } from "../content/sections";
import type { AllData } from "../lib/data";
import { num } from "../lib/format";

function frDate(iso: string): string {
  return new Date(`${iso}T12:00:00`).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
}

const STATUS: Record<string, { label: string; icon: string }> = {
  ok: { label: "conforme", icon: "✓" },
  attention: { label: "traité", icon: "!" },
  info: { label: "information", icon: "i" },
};

const PIPELINE = [
  { step: "Acquisition", text: "4TU.ResearchData, sinon copie publique pm4py-core ; empreinte et comptes vérifiés." },
  { step: "Ingestion", text: "XES vers Parquet, ordre canonique des jalons simultanés." },
  { step: "Qualité", text: "14 contrôles, règles de nettoyage des sessions." },
  { step: "Découverte", text: "Carte des flux, variantes, alignements, inductive miner." },
  { step: "KPI", text: "Délais, attente, travail, goulots, charge, reprises, abandons." },
  { step: "Modèle", text: "Préfixes au point de décision, validation temporelle, SHAP." },
  { step: "Business case", text: "Rejeu contrefactuel, Monte Carlo, VAN, sensibilité." },
  { step: "Exports", text: "JSON du site, BPMN, documents chiffrés générés." },
];

export default function Method({ data }: { data: AllData }) {
  const [showLabels, setShowLabels] = useState(false);
  const meta = data.meta;
  const checks = data.quality.checks;
  const acts = data.labels.activities;
  return (
    <Section
      id="methode"
      num="10"
      kicker="Méthode et données"
      title={<>Un journal public, {num(meta.counts.events)} événements, une seule commande pour tout recalculer.</>}
      lede={
        <>
          Données : {meta.dataset.name}, journal d'événements d'une institution financière néerlandaise
          ({frDate(meta.window.first_submission)} → {frDate(meta.window.last_event)}). Citation obligatoire : {meta.dataset.citation}{" "}
          <a href={meta.dataset.doi}>{meta.dataset.doi.replace("https://", "")}</a>, conditions « {meta.dataset.terms} ».
        </>
      }
    >
      <div className="grid">
        <Reveal className="span-12">
          <ol className="line-steps pipeline">
            {PIPELINE.map((p, i) => (
              <li key={p.step}>
                <span className="line-steps-num">{String(i + 1).padStart(2, "0")}</span>
                <span className="line-steps-title">{p.step}</span>
                <span className="line-steps-text">{p.text}</span>
              </li>
            ))}
          </ol>
          <p className="source">
            Graine fixe ({meta.seed}) ; deux exécutions successives produisent des exports identiques. Commandes :{" "}
            <code>make all</code> (tout), <code>make pipeline</code> (analyses), <code>make data</code> (données).{" "}
            <a href={REPO_URL}>Code source</a>.
          </p>
        </Reveal>

        <Reveal className="span-7">
          <h3 className="h3">Contrôles de qualité des données</h3>
          <div className="table-wrap">
            <table className="data quality-table">
              <thead>
                <tr>
                  <th scope="col">Contrôle</th>
                  <th scope="col">Résultat</th>
                  <th scope="col">Traitement</th>
                </tr>
              </thead>
              <tbody>
                {checks.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <span className={`qstatus ${c.status}`} aria-label={STATUS[c.status].label} title={STATUS[c.status].label}>
                        {STATUS[c.status].icon}
                      </span>
                      {c.label}
                    </td>
                    <td>
                      {c.value}
                      <br />
                      <span className="muted small">{c.detail}</span>
                    </td>
                    <td className="small">{c.treatment}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Reveal>
        <Reveal className="span-5" delay={0.06}>
          <h3 className="h3">Limites</h3>
          <ul className="facts">
            <li>Cinq mois observés : volumes annualisés (× {num(meta.window.annual_factor, 2)}), saisonnalité inconnue, encadrée dans le Monte Carlo.</li>
            <li>Le journal ne contient ni motif d'annulation, ni pièce justificative, ni donnée client autre que le montant.</li>
            <li>Les heures de travail sont estimées après nettoyage des sessions restées ouvertes : estimation prudente.</li>
            <li>Les coûts de construction et de fonctionnement sont des hypothèses d'ordre de grandeur, à remplacer par des devis.</li>
            <li>Le business case valorise la capacité libérée : elle ne devient une économie que si elle est redéployée.</li>
          </ul>
          <h3 className="h3">Documents</h3>
          <ul className="facts">
            <li><a href={docUrl("docs/01-note-de-cadrage.md")}>Note de cadrage</a></li>
            <li><a href={docUrl("docs/02-analyse-as-is.md")}>Analyse AS-IS chiffrée</a></li>
            <li><a href={docUrl("docs/04-user-stories.md")}>User stories et critères d'acceptation</a></li>
            <li><a href={docUrl("docs/05-business-case.md")}>Business case détaillé</a></li>
            <li><a href={docUrl("docs/07-plan-de-recette.md")}>Plan de recette</a></li>
            <li><a href={docUrl("docs/08-conduite-du-changement.md")}>Conduite du changement</a></li>
            <li><a href={docUrl("docs/decisions.md")}>Journal des décisions</a></li>
          </ul>
        </Reveal>

        <Reveal className="span-12">
          <div className="labels-head">
            <h3 className="h3">Table de traduction des activités</h3>
            <button type="button" className="table-toggle" aria-expanded={showLabels} onClick={() => setShowLabels((v) => !v)}>
              {showLabels ? "Masquer la table" : `Afficher les ${acts.length} activités`}
            </button>
          </div>
          {showLabels && (
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th scope="col">Code du journal</th>
                    <th scope="col">Libellé</th>
                    <th scope="col">Type</th>
                    <th scope="col">Description</th>
                  </tr>
                </thead>
                <tbody>
                  {acts.map((a) => (
                    <tr key={a.code}>
                      <td className="narrow">{a.code}</td>
                      <td>{a.label}</td>
                      <td>{a.category_label}</td>
                      <td className="small">{a.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Reveal>
      </div>
    </Section>
  );
}
