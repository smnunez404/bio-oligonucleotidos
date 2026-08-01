import { useState } from "react";
import type { RankingResponse } from "../types";
import { InfoTip } from "./InfoTip";

interface Props {
  data: RankingResponse;
  selected: string | null;
  onSelect: (name: string | null) => void;
}

/**
 * Tabla del Módulo 7. A diferencia de las tablas anteriores, esta NO es
 * ordenable por columna a gusto: el orden es frente-primero y después por fuerza
 * de bloqueo. Dejar reordenar por cualquier columna invitaría a leer la primera
 * fila como "el ganador", que es exactamente la lectura que un frente de Pareto
 * no autoriza.
 *
 * La columna "dominado por" es la que hace auditable el resultado: cualquier
 * candidato fuera del frente puede justificar por qué, con nombre y apellido.
 */
export function RankingTable({ data, selected, onSelect }: Props) {
  const [onlyFront, setOnlyFront] = useState(false);
  const rows = onlyFront ? data.candidates.filter((c) => c.in_front) : data.candidates;

  return (
    <div className="card">
      <h2>Los {data.n_eligible} candidatos que anulan el pseudoexón</h2>
      <p className="muted">{data.gate}</p>

      <div className="filter-row">
        <label>
          <input
            type="checkbox"
            checked={onlyFront}
            onChange={(e) => setOnlyFront(e.target.checked)}
          />{" "}
          Mostrar solo el frente ({data.front.length} de {data.n_eligible})
        </label>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>Candidato</th>
            <th>Ventana</th>
            <th>Anula</th>
            <th>
              Bloqueo{" "}
              <InfoTip text="Cuánto se apaga el borde del pseudoexón que el ASO logra anular, promediado entre los dos predictores. 1,000 = el sitio queda completamente apagado." />
            </th>
            <th>
              Off-target{" "}
              <InfoTip text="El tramo seguido más largo que coincide perfecto con un gen que NO es ABCA4. Menos pares de bases = menos riesgo de pegarse donde no debe." />
            </th>
            <th>
              Termodinámica{" "}
              <InfoTip text="Promedio de dos percentiles del Módulo 4: qué tan alcanzable está la zona del ARN, y qué tan poco tiende el oligo a pegarse consigo mismo. Más alto = mejor." />
            </th>
            <th>Dominado por</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((c) => {
            const isSel = selected === c.name;
            return (
              <tr
                key={c.name}
                onClick={() => onSelect(isSel ? null : c.name)}
                style={{
                  cursor: "pointer",
                  fontWeight: c.in_front ? 600 : 400,
                  background: isSel ? "#fef3c7" : c.in_front ? "#f0fdfa" : undefined,
                }}
              >
                <td>
                  {c.in_front ? "🟢 " : "⚪ "}
                  {c.name}
                </td>
                <td>
                  {c.start_rel} … {c.end_rel}
                </td>
                <td>{c.borders_abolished.join(" + ") || "—"}</td>
                <td>{c.objectives.block_strength.toFixed(5)}</td>
                <td>
                  {c.raw.longest_perfect_run} pb{" "}
                  <span className="muted">({c.severity})</span>
                </td>
                <td>{c.objectives.thermo_quality.toFixed(1)}</td>
                <td className="muted">
                  {c.in_front ? "— (nadie)" : c.dominated_by.join(", ")}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <p className="muted">
        <strong>Procedencia:</strong> {data.provenance_caveat}
      </p>
    </div>
  );
}
