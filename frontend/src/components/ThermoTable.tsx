import { useState } from "react";
import type { ThermoCandidate } from "../types";
import { InfoTip } from "./InfoTip";
import { glossary } from "../glossary";

interface Props {
  candidates: ThermoCandidate[];
  /** Rango [inicio, fin) del sitio donador críptico, para marcar solapamiento. */
  donorRange?: [number, number];
}

type OrderKey = "accessibility" | "position";

export function ThermoTable({ candidates, donorRange }: Props) {
  const [onlyPassed, setOnlyPassed] = useState(true);
  const [order, setOrder] = useState<OrderKey>("accessibility");

  const overlapsDonor = (c: ThermoCandidate) =>
    donorRange ? c.start < donorRange[1] && c.end > donorRange[0] : false;

  let rows = onlyPassed ? candidates.filter((c) => c.passed) : candidates;
  rows = [...rows].sort((a, b) =>
    order === "accessibility"
      ? (b.accessibility_percentile ?? -1) - (a.accessibility_percentile ?? -1)
      : a.start - b.start
  );

  return (
    <div className="card">
      <h2>Candidatos analizados</h2>
      <div className="controls-row">
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={onlyPassed}
            onChange={(e) => setOnlyPassed(e.target.checked)}
          />
          Solo aprobados ({candidates.filter((c) => c.passed).length} de{" "}
          {candidates.length})
        </label>
        <label className="checkbox-row">
          Ordenar por:{" "}
          <select
            value={order}
            onChange={(e) => setOrder(e.target.value as OrderKey)}
          >
            <option value="accessibility">Accesibilidad</option>
            <option value="position">Posición</option>
          </select>
        </label>
      </div>

      <div className="table-scroll">
        <table className="candidates-table">
          <thead>
            <tr>
              <th>Posición</th>
              <th>
                <InfoTip text={glossary.meltingTemp}>Tm</InfoTip>
              </th>
              <th>
                <InfoTip text={glossary.hairpin}>Horquilla</InfoTip>
              </th>
              <th>
                <InfoTip text={glossary.homodimer}>Homodímero</InfoTip>
              </th>
              <th>
                <InfoTip text={glossary.accessibility}>Accesib.</InfoTip>{" "}
                <InfoTip text={glossary.percentile}>(pct)</InfoTip>
              </th>
              <th>Sitio crítico</th>
              <th>¿Aprobado?</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.start} className={overlapsDonor(c) ? "row-donor" : undefined}>
                <td className="mono">
                  {c.start}–{c.end}
                </td>
                <td className="mono">{c.tm.toFixed(1)} °C</td>
                <td className="mono">{c.dg_self_structure.toFixed(1)}</td>
                <td className="mono">{c.dg_homodimer.toFixed(1)}</td>
                <td className="mono">
                  {c.accessibility_percentile !== null
                    ? `p${c.accessibility_percentile.toFixed(0)}`
                    : "—"}
                </td>
                <td>{overlapsDonor(c) ? "🎯 donador" : c.covers_variant ? "variante" : "—"}</td>
                <td>
                  {c.passed ? "✅" : "❌"}
                  {c.reasons.length > 0 && (
                    <span className="muted"> {c.reasons.join("; ")}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
