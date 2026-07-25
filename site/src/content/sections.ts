/** Plan du rapport : identifiants d'ancre, numéros et titres courts. */
export const SECTIONS = [
  { id: "synthese", num: "01", short: "Synthèse" },
  { id: "demarche", num: "02", short: "Démarche" },
  { id: "parcours", num: "03", short: "Parcours" },
  { id: "temps", num: "04", short: "Temps" },
  { id: "allers-retours", num: "05", short: "Reprises" },
  { id: "abandons", num: "06", short: "Abandons" },
  { id: "prediction", num: "07", short: "Prédiction" },
  { id: "business-case", num: "08", short: "Business case" },
  { id: "conformite", num: "09", short: "Conformité" },
  { id: "methode", num: "10", short: "Méthode" },
] as const;

export const REPO_URL = "https://github.com/youssefmir/credit-process-intelligence";
export const AUTHOR_URL = "https://github.com/youssefmir";
export const DEMO_URL = "https://credit-process-intelligence.vercel.app/";

export function docUrl(path: string): string {
  return `${REPO_URL}/blob/main/${path}`;
}
