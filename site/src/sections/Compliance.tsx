import Reveal from "../components/Reveal";
import Section from "../components/Section";
import { ASSESSMENTS, MILESTONES, SOURCES } from "../content/compliance";
import { docUrl } from "../content/sections";
import type { AllData } from "../lib/data";

export default function Compliance({ data }: { data: AllData }) {
  void data;
  return (
    <Section
      id="conformite"
      num="09"
      kicker="Conformité et risques"
      title="Aucune des trois opportunités ne décide du crédit : c'est ce qui les tient hors du haut risque."
      lede="Le crédit à la consommation est un terrain réglementé : l'évaluation de la solvabilité par une IA relève du haut risque de l'AI Act, et le profilage des clients du RGPD. Chaque opportunité est qualifiée, avec ses garde-fous."
    >
      <Reveal>
        <ol className="timeline" aria-label="Calendrier réglementaire">
          {MILESTONES.map((m) => (
            <li key={m.iso} className={m.kind}>
              <span className="timeline-date num">{m.date}</span>
              <span className="timeline-dot" aria-hidden="true" />
              <span className="timeline-title">{m.title}</span>
              <span className="timeline-text">{m.text}</span>
            </li>
          ))}
        </ol>
        <p className="source">État au 2 novembre 2026. Les obligations haut risque de l'annexe III ont été reportées au 2 décembre 2027 par le règlement (UE) 2026/1744 (JO du 24 juillet 2026).</p>
      </Reveal>

      <Reveal>
        <div className="table-wrap">
          <table className="data compliance-table">
            <caption className="sr-only">Qualification AI Act et RGPD des trois opportunités</caption>
            <thead>
              <tr>
                <th scope="col">Opportunité</th>
                <th scope="col">AI Act</th>
                <th scope="col">RGPD et droit du crédit</th>
                <th scope="col">Risques et garde-fous</th>
              </tr>
            </thead>
            <tbody>
              {ASSESSMENTS.map((a) => (
                <tr key={a.opp}>
                  <th scope="row">{a.opp}</th>
                  <td>{a.aiAct}</td>
                  <td>{a.gdpr}</td>
                  <td>
                    <span className="muted">{a.risks}</span>
                    <br />
                    {a.safeguards}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Reveal>

      <Reveal className="grid compliance-foot">
        <div className="span-6">
          <h3 className="h3">Limites assumées</h3>
          <ul className="facts">
            <li>Aucun attribut sensible dans les données : l'équité entre groupes protégés ne peut pas être mesurée ; seule la stabilité par tranche de montant l'est.</li>
            <li>Le journal est anonymisé et ancien (2011-2012) ; les qualifications portent sur des cas d'usage, pas sur un système déployé.</li>
            <li>Cette analyse n'est pas un avis juridique : elle prépare l'instruction par la conformité et le délégué à la protection des données.</li>
          </ul>
          <p>
            <a href={docUrl("docs/06-conformite-ia-rgpd.md")}>Lire l'analyse complète AI Act et RGPD</a>
          </p>
        </div>
        <div className="span-6">
          <h3 className="h3">Sources</h3>
          <ul className="sources">
            {SOURCES.map((s) => (
              <li key={s.url}>
                <a href={s.url}>{s.label}</a>
              </li>
            ))}
          </ul>
        </div>
      </Reveal>
    </Section>
  );
}
