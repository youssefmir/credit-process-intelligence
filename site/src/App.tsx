import Footer from "./components/Footer";
import Header from "./components/Header";
import { useAllData } from "./lib/data";
import Hero from "./sections/Hero";
import Summary from "./sections/Summary";
import Approach from "./sections/Approach";
import Process from "./sections/Process";
import TimeLost from "./sections/TimeLost";
import Rework from "./sections/Rework";
import Abandon from "./sections/Abandon";
import Prediction from "./sections/Prediction";

export default function App() {
  const { data, error } = useAllData();
  return (
    <>
      <a className="skip-link" href="#synthese">
        Aller au contenu
      </a>
      <Header />
      <main>
        {error && (
          <p className="wrap" role="alert">
            Les données du rapport n'ont pas pu être chargées ({error}).
          </p>
        )}
        {!data && !error && (
          <p className="wrap loading" aria-live="polite">
            Chargement des données…
          </p>
        )}
        {data && (
          <>
            <Hero data={data} />
            <Summary data={data} />
            <Approach />
            <Process data={data} />
            <TimeLost data={data} />
            <Rework data={data} />
            <Abandon data={data} />
            <Prediction data={data} />
          </>
        )}
      </main>
      <Footer />
    </>
  );
}
