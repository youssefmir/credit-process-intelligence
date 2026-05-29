/** Repères réglementaires vérifiés (novembre 2026) et sources. */

export interface Milestone {
  date: string;
  iso: string;
  title: string;
  text: string;
  kind: "past" | "now" | "future";
}

export const MILESTONES: Milestone[] = [
  { date: "1er août 2024", iso: "2024-08-01", title: "Entrée en vigueur de l'AI Act", text: "Règlement (UE) 2024/1689.", kind: "past" },
  { date: "2 février 2025", iso: "2025-02-02", title: "Interdictions et culture de l'IA", text: "Pratiques interdites (article 5) et obligation de formation (article 4).", kind: "past" },
  { date: "2 août 2025", iso: "2025-08-02", title: "Modèles d'IA à usage général", text: "Obligations des fournisseurs de modèles (GPAI), dont les modèles de langage.", kind: "past" },
  { date: "2 août 2026", iso: "2026-08-02", title: "Transparence (article 50)", text: "Informer les personnes qu'elles interagissent avec une IA ; marquage des contenus générés, avec délai jusqu'au 2 décembre 2026 pour les systèmes déjà en service.", kind: "past" },
  { date: "20 novembre 2026", iso: "2026-11-20", title: "Directive crédit à la consommation (CCD2)", text: "Directive (UE) 2023/2225 : évaluation de solvabilité (article 18) et droit à une intervention humaine en cas de traitement automatisé.", kind: "now" },
  { date: "2 décembre 2027", iso: "2027-12-02", title: "Haut risque, annexe III", text: "Report par le règlement « omnibus numérique » (UE) 2026/1744 ; inclut l'évaluation de la solvabilité et le score de crédit (annexe III, point 5 b).", kind: "future" },
  { date: "2 août 2028", iso: "2028-08-02", title: "Haut risque, annexe I", text: "IA intégrée à des produits réglementés.", kind: "future" },
];

export interface Assessment {
  opp: string;
  aiAct: string;
  gdpr: string;
  risks: string;
  safeguards: string;
}

export const ASSESSMENTS: Assessment[] = [
  {
    opp: "Contrôle de complétude",
    aiAct:
      "Hors annexe III tant qu'il se limite à vérifier la présence, la lisibilité et la validité des pièces (tâche procédurale étroite, article 6.3). Transparence (article 50) si un agent conversationnel guide le client.",
    gdpr: "Mesures précontractuelles (article 6.1 b). Minimisation des pièces, durées de conservation, sous-traitant de lecture documentaire encadré (article 28).",
    risks: "Pièce jugée manquante à tort, friction au dépôt, moins bonne lecture de certains documents (étrangers, scans).",
    safeguards: "Aucun refus automatique ; alerte contestable ; taux d'erreur suivi par type de pièce ; repli vers un conseiller.",
  },
  {
    opp: "Relances priorisées",
    aiAct:
      "Risque minimal : le score ordonne une file de relance et n'évalue pas la solvabilité. Il deviendrait haut risque s'il servait un jour à l'octroi ou aux conditions du crédit.",
    gdpr:
      "Profilage (article 4.4) fondé sur l'intérêt légitime avec mise en balance, information des clients (articles 13-14), droit d'opposition (article 21), analyse d'impact (AIPD) recommandée. Pas de décision exclusivement automatisée (article 22), à condition que le score n'influence jamais l'octroi (arrêt SCHUFA, CJUE C-634/21).",
    risks: "Glissement d'usage vers la décision, traitement différencié des clients, dérive du modèle.",
    safeguards: "Usage limité par écrit à la relance ; aucune transmission aux équipes d'octroi ; suivi trimestriel (PSI, performance) ; pilote A/B avant tout déploiement.",
  },
  {
    opp: "Pré-analyse assistée",
    aiAct:
      "La plus sensible : elle s'insère dans le processus d'octroi. Présumée haut risque (annexe III, point 5 b) sauf démonstration documentée d'une tâche préparatoire sans profilage (articles 6.3 et 6.4, enregistrement article 49.2). Sinon : gestion des risques, gouvernance des données, documentation, journalisation, contrôle humain (article 14), au plus tard le 2 décembre 2027. Le fournisseur du modèle de langage a ses propres obligations depuis août 2025.",
    gdpr:
      "Données financières sensibles : AIPD obligatoire, sous-traitance et transferts encadrés, aucune donnée réelle dans les invites sans base légale. CCD2 : l'analyste garde l'évaluation de solvabilité.",
    risks: "Erreurs ou omissions de la synthèse, biais d'automatisation de l'analyste, dépendance à un prestataire (DORA).",
    safeguards: "Fiche factuelle relue et corrigée par l'analyste ; sources citées pour chaque point ; échantillon de contrôle qualité ; plan de réversibilité du prestataire.",
  },
];

export const SOURCES = [
  { label: "Règlement (UE) 2024/1689 (AI Act), EUR-Lex", url: "https://eur-lex.europa.eu/eli/reg/2024/1689/oj" },
  { label: "EU Digital Omnibus on AI enters into force (National Law Review)", url: "https://natlawreview.com/article/eu-digital-omnibus-ai-enters-force" },
  { label: "EU AI Act high-risk deadline: deferred, not cancelled (Cloud Security Alliance)", url: "https://labs.cloudsecurityalliance.org/research/csa-research-note-eu-ai-act-high-risk-deadline-omnibus-20260/" },
  { label: "AI Omnibus adopted: what still applies from August 2 (iubenda)", url: "https://www.iubenda.com/en/blog/ai-omnibus-adopted-august-2-obligations-july-2026/" },
  { label: "Directive (UE) 2023/2225 relative aux contrats de crédit aux consommateurs", url: "https://eur-lex.europa.eu/eli/dir/2023/2225/oj" },
  { label: "CJUE, 7 décembre 2023, SCHUFA Holding (Scoring), C-634/21", url: "https://curia.europa.eu/juris/liste.jsf?num=C-634/21" },
  { label: "Règlement (UE) 2016/679 (RGPD)", url: "https://eur-lex.europa.eu/eli/reg/2016/679/oj" },
];
