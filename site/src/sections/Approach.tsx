import Reveal from "../components/Reveal";
import Section from "../components/Section";
import { docUrl } from "../content/sections";

const STEPS = [
  { title: "Cadrage", text: "Questions métier, périmètre, critères de succès, parties prenantes.", doc: "docs/01-note-de-cadrage.md" },
  { title: "Données et qualité", text: "Acquisition reproductible, 14 contrôles chiffrés, règles de nettoyage.", doc: "docs/02-analyse-as-is.md" },
  { title: "Process mining", text: "Carte des flux, variantes, conformité au chemin nominal, modèle découvert.", doc: "docs/02-analyse-as-is.md" },
  { title: "Diagnostic", text: "Délais, attente contre travail, goulots, allers-retours, abandons.", doc: "docs/02-analyse-as-is.md" },
  { title: "Modélisation", text: "BPMN AS-IS et TO-BE, user stories, prédiction des abandons.", doc: "docs/03-modelisation-bpmn.md" },
  { title: "Business case", text: "Rejeu contrefactuel des dossiers, Monte Carlo, VAN, sensibilité.", doc: "docs/05-business-case.md" },
  { title: "Conformité et adoption", text: "AI Act, RGPD, plan de recette, conduite du changement.", doc: "docs/06-conformite-ia-rgpd.md" },
];

export default function Approach() {
  return (
    <Section
      id="demarche"
      num="02"
      kicker="La démarche Business Analyst"
      title="Partir des traces réelles, pas des intuitions"
      lede="Sept étapes, chacune avec un livrable versionné dans le dépôt. Chaque chiffre du rapport est recalculé par une seule commande (make all) à partir du journal public."
    >
      <Reveal>
        <ol className="line-steps">
          {STEPS.map((s, i) => (
            <li key={s.title}>
              <span className="line-steps-num">{String(i + 1).padStart(2, "0")}</span>
              <span className="line-steps-title">{s.title}</span>
              <span className="line-steps-text">{s.text}</span>
              <a className="small" href={docUrl(s.doc)}>
                Livrable
              </a>
            </li>
          ))}
        </ol>
      </Reveal>
    </Section>
  );
}
