import { useId, useState, type ReactNode } from "react";

export interface TableSpec {
  columns: string[];
  rows: (string | number)[][];
  /** Colonnes alignées à droite (valeurs numériques). */
  numeric?: number[];
}

interface Props {
  title: string;
  subtitle?: string;
  source?: string;
  table?: TableSpec;
  children: ReactNode;
  className?: string;
}

/** Conteneur de graphique : titre, sous-titre, vue tableau (jumeau accessible), source. */
export default function Figure({ title, subtitle, source, table, children, className }: Props) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <figure className={`chart ${className ?? ""}`} aria-labelledby={`${id}-t`}>
      <figcaption>
        <div>
          <div id={`${id}-t`} className="chart-title">
            {title}
          </div>
          {subtitle && <div className="chart-sub">{subtitle}</div>}
        </div>
        {table && (
          <button type="button" className="table-toggle" aria-expanded={open} aria-controls={`${id}-tbl`} onClick={() => setOpen((v) => !v)}>
            {open ? "Masquer les données" : "Voir les données"}
          </button>
        )}
      </figcaption>
      {children}
      {table && open && (
        <div className="table-wrap" id={`${id}-tbl`}>
          <table className="data">
            <caption className="sr-only">{title}</caption>
            <thead>
              <tr>
                {table.columns.map((c, i) => (
                  <th key={c} className={table.numeric?.includes(i) ? "r" : undefined} scope="col">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.rows.map((row, r) => (
                <tr key={r}>
                  {row.map((cell, i) => (
                    <td key={i} className={table.numeric?.includes(i) ? "r" : undefined}>
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {source && <p className="source">{source}</p>}
    </figure>
  );
}
