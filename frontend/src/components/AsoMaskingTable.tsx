import { useState } from "react";
import type { AsoMaskingClass, AsoMaskingResponse } from "../types";
import { InfoTip } from "./InfoTip";
import { glossary } from "../glossary";

interface Props {
  data: AsoMaskingResponse;
  selected: string | null;
  onSelect: (name: string | null) => void;
}

const CLASS_ORDER: AsoMaskingClass[] = ["bloquea", "contraproducente", "sin_efecto"];
const CLASS_ICON: Record<AsoMaskingClass, string> = {
  bloquea: "🟢",
  contraproducente: "🔴",
  sin_efecto: "⚪",
};
const CLASS_LABEL: Record<AsoMaskingClass, string> = {
  bloquea: "apaga el sitio falso",
  contraproducente: "lo empeora",
  sin_efecto: "sin efecto",
};

type OrderKey = "delta_donor" | "position";

/**
 * Tabla del Módulo 6b. Ordena por defecto por el efecto sobre el sitio falso
 * (de más negativo = mejor, a más positivo = peor), que es la única columna de
 * este módulo que tiene DIRECCIÓN biológica; los módulos anteriores ordenaban
 * por propiedades físicas del oligo, que no distinguen ayudar de perjudicar.
 *
 * Este módulo NO descarta candidatos: clasifica. La decisión de excluir a los
 * contraproducentes es del Módulo 7 (ranking).
 */
export function AsoMaskingTable({ data, selected, onSelect }: Props) {
  const [classFilter, setClassFilter] = useState<AsoMaskingClass | "todos">("todos");
  const [order, setOrder] = useState<OrderKey>("delta_donor");

  let rows =
    classFilter === "todos"
      ? data.candidates
      : data.candidates.filter((c) => c.classification === classFilter);
  rows = [...rows].sort((a, b) =>
    order === "delta_donor" ? a.delta_donor - b.delta_donor : a.start_rel - b.start_rel
  );

  return (
    <div className="card">
      <h2>
        Los {data.total} candidatos, ordenados por{" "}
        <InfoTip text={glossary.asoMasking}>efecto sobre el sitio falso</InfoTip>
      </h2>

      <div className="filter-row">
        <label>
          Mostrar:{" "}
          <select
            value={classFilter}
            onChange={(e) => setClassFilter(e.target.value as AsoMaskingClass | "todos")}
          >
            <option value="todos">todos ({data.total})</option>
            {CLASS_ORDER.map((k) => (
              <option key={k} value={k}>
                {CLASS_ICON[k]} {CLASS_LABEL[k]} ({data.counts[k] ?? 0})
              </option>
            ))}
          </select>
        </label>
        <label>
          Ordenar por:{" "}
          <select value={order} onChange={(e) => setOrder(e.target.value as OrderKey)}>
            <option value="delta_donor">efecto sobre el sitio falso</option>
            <option value="position">posición</option>
          </select>
        </label>
        <span className="muted">{rows.length} en pantalla</span>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>Candidato</th>
            <th>Se pega en</th>
            <th>¿Tapa el sitio falso?</th>
            <th>Sitio falso de salida</th>
            <th>Sitio falso de entrada</th>
            <th>Sitio sano E3</th>
            <th>Clasificación</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((c) => (
            <tr
              key={c.name}
              className={c.name === selected ? "row-selected" : undefined}
              onClick={() => onSelect(c.name === selected ? null : c.name)}
              style={{ cursor: "pointer" }}
            >
              <td>{c.name}</td>
              <td>
                {c.start_rel} … {c.end_rel}
              </td>
              <td>{c.covers_donor ? "sí" : "no"}</td>
              <td className={c.retention_donor < data.thresholds.block_retention ? "cell-good" : c.retention_donor - 1 >= data.thresholds.counterproductive_gain ? "cell-bad" : undefined}>
                {c.donor_cryptic.toFixed(4)}{" "}
                <span className="muted">
                  ({c.delta_donor >= 0 ? "+" : ""}
                  {c.delta_donor.toFixed(4)})
                </span>
              </td>
              <td>
                {c.acceptor_cryptic.toFixed(4)}{" "}
                <span className="muted">
                  ({c.delta_acceptor >= 0 ? "+" : ""}
                  {c.delta_acceptor.toFixed(4)})
                </span>
              </td>
              <td>
                <span className="muted">
                  {c.delta_canonical >= 0 ? "+" : ""}
                  {c.delta_canonical.toFixed(4)}
                </span>
              </td>
              <td>
                {CLASS_ICON[c.classification]} {CLASS_LABEL[c.classification]}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="muted">
        Los valores son probabilidades que da el predictor, entre 0 y 1. Sin
        ningún parche, el sitio falso de salida vale{" "}
        {data.baseline.donor_cryptic.toFixed(4)} y el de entrada{" "}
        {data.baseline.acceptor_cryptic.toFixed(4)}. La última columna verifica
        que el parche no toque el sitio SANO del exón 3 (que vale{" "}
        {data.baseline.donor_canonical_e3.toFixed(4)} y debe quedarse ahí).
      </p>
    </div>
  );
}
