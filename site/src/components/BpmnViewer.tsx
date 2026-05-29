import "bpmn-js/dist/assets/diagram-js.css";
import "bpmn-js/dist/assets/bpmn-js.css";

import NavigatedViewer from "bpmn-js/lib/NavigatedViewer";
import { useEffect, useRef, useState } from "react";

import { docUrl } from "../content/sections";

type Model = "as-is" | "to-be";

const LABEL: Record<Model, string> = { "as-is": "AS-IS : processus observé", "to-be": "TO-BE : processus cible" };

/** Visionneuse BPMN (bpmn-js) : bascule AS-IS / TO-BE, zoom et déplacement. */
export default function BpmnViewer() {
  const host = useRef<HTMLDivElement | null>(null);
  const viewer = useRef<NavigatedViewer | null>(null);
  const [model, setModel] = useState<Model>("as-is");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!host.current) return;
    const v = new NavigatedViewer({
      container: host.current,
      bpmnRenderer: { defaultFillColor: "#ffffff", defaultStrokeColor: "#111111", defaultLabelColor: "#111111" },
    });
    viewer.current = v;
    return () => {
      v.destroy();
      viewer.current = null;
    };
  }, []);

  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    let alive = true;
    fetch(`${import.meta.env.BASE_URL}bpmn/${model}.bpmn`)
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.text();
      })
      .then((xml) => v.importXML(xml))
      .then(() => {
        if (!alive) return;
        const canvas = v.get("canvas") as { zoom: (z: string | number) => void };
        canvas.zoom("fit-viewport");
        setError(null);
      })
      .catch((e: unknown) => alive && setError(String(e)));
    return () => {
      alive = false;
    };
  }, [model]);

  const zoom = (factor: number | "fit") => {
    const v = viewer.current;
    if (!v) return;
    const canvas = v.get("canvas") as { zoom: (z?: string | number) => number };
    if (factor === "fit") canvas.zoom("fit-viewport");
    else canvas.zoom(canvas.zoom() * factor);
  };

  return (
    <div className="bpmn">
      <div className="controls">
        <div className="seg" role="tablist" aria-label="Modèle affiché">
          {(["as-is", "to-be"] as Model[]).map((m) => (
            <button key={m} type="button" role="tab" aria-selected={model === m} onClick={() => setModel(m)}>
              {LABEL[m]}
            </button>
          ))}
        </div>
        <div className="seg" role="group" aria-label="Zoom">
          <button type="button" onClick={() => zoom(1.25)} aria-label="Zoomer">+</button>
          <button type="button" onClick={() => zoom(0.8)} aria-label="Dézoomer">−</button>
          <button type="button" onClick={() => zoom("fit")}>Ajuster</button>
        </div>
      </div>
      <div ref={host} className="bpmn-canvas" role="img" aria-label={`Diagramme BPMN ${LABEL[model]}`} />
      {error && <p className="small">Diagramme indisponible ({error}).</p>}
      <p className="source">
        BPMN 2.0 généré par le pipeline (annotations chiffrées), lisible dans tout outil conforme :{" "}
        <a href={docUrl("docs/bpmn/as-is.bpmn")}>as-is.bpmn</a> · <a href={docUrl("docs/bpmn/to-be.bpmn")}>to-be.bpmn</a>.
        Glisser pour se déplacer ; en jaune les boucles de reprise, en bleu les apports de l'IA.
      </p>
    </div>
  );
}
