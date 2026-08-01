import { useState } from "react";
import type { OligoCandidate } from "../types";
import { InfoTip } from "./InfoTip";
import { glossary } from "../glossary";

interface Props {
  candidates: OligoCandidate[];
}

export function OligoWalkTable({ candidates }: Props) {
  const [onlyCovering, setOnlyCovering] = useState(false);
  const rows = onlyCovering ? candidates.filter((c) => c.covers_variant) : candidates;

  return (
    <div className="card">
      <h2>Todos los candidatos generados</h2>
      <label className="checkbox-row">
        <input
          type="checkbox"
          checked={onlyCovering}
          onChange={(e) => setOnlyCovering(e.target.checked)}
        />
        <InfoTip text={glossary.coversVariant}>
          Mostrar solo los que cubren la mutación
        </InfoTip>{" "}
        ({candidates.filter((c) => c.covers_variant).length} de {candidates.length})
      </label>

      <div className="table-scroll">
        <table className="candidates-table">
          <thead>
            <tr>
              <th>Posición</th>
              <th>Distancia a la variante</th>
              <th>
                <InfoTip text={glossary.antisenseSequence}>ASO (antisentido)</InfoTip>
              </th>
              <th>¿Cubre la mutación?</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.start} className={c.covers_variant ? "row-covers" : undefined}>
                <td className="mono">{c.start}–{c.end}</td>
                <td className="mono">{c.distance_to_variant > 0 ? "+" : ""}{c.distance_to_variant}</td>
                <td className="mono">{c.aso_sequence}</td>
                <td>{c.covers_variant ? "✅" : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
