import { AUTHOR_URL, REPO_URL } from "../content/sections";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="wrap footer-inner">
        <p className="footer-sign">Projet réalisé par Youssef Mir — Business Analyst IA</p>
        <ul className="footer-links">
          <li>
            <a href={AUTHOR_URL}>github.com/youssefmir</a>
          </li>
          <li>
            <a href={REPO_URL}>Dépôt du projet</a>
          </li>
        </ul>
        <p className="small muted footer-data">
          Données : BPI Challenge 2012 (van Dongen, 2012, 4TU.ResearchData, conditions « 4TU General Terms of Use »).
          Code sous licence MIT.
        </p>
      </div>
    </footer>
  );
}
