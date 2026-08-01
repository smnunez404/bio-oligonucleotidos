import { useState } from "react";
import type { FilteredCandidate } from "../types";
import { InfoTip } from "./InfoTip";
import { glossary } from "../glossary";

interface Props {
  candidates: FilteredCandidate[];
}

export function FilterTable({ candidates }: Props) {
  const [onlyPassed, setOnlyPassed] = useState(true);
  const rows = onlyPassed ? candidates.filter((c) => c.passed) : candidates;

  return (
    <div className="card">
      <h2>Candidatos con resultado del filtro</h2>
      <label className="checkbox-row">
        <input
          type="checkbox"
          checked={onlyPassed}
          onChange={(e) => setOnlyPassed(e.target.checked)}
        />
        Mostrar solo los aprobados ({candidates.filter((c) => c.passed).length} de{" "}
        {candidates.length})
      </label>

      <div className="table-scroll">
        <table className="candidates-table">
          <thead>
            <tr>
              <th>Posición</th>
              <th>
                <InfoTip text={glossary.antisenseSequence}>ASO</InfoTip>
              </th>
              <th>
                <InfoTip text={glossary.gcContent}>GC%</InfoTip>
              </th>
              <th>
                <InfoTip text={glossary.gRun}>G-run</InfoTip>
              </th>
              <th>
                <InfoTip text={glossary.passedFilter}>¿Aprobado?</InfoTip>
              </th>
              <th>Motivo del rechazo</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.start} className={c.passed ? "row-covers" : undefined}>
                <td className="mono">{c.start}–{c.end}</td>
                <td className="mono">{c.aso_sequence}</td>
                <td className="mono">{(c.gc_fraction * 100).toFixed(0)}%</td>
                <td>{c.has_g_run ? "⚠️" : "—"}</td>
                <td>{c.passed ? "✅" : "❌"}</td>
                <td className="muted">{c.reasons.join("; ") || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
