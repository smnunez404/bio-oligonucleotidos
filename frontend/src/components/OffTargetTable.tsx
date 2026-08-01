import { Fragment, useState } from "react";
import type { OffTargetCandidate, OffTargetSeverity } from "../types";
import { InfoTip } from "./InfoTip";
import { glossary } from "../glossary";

interface Props {
  candidates: OffTargetCandidate[];
}

type OrderKey = "longest_perfect_run" | "off_target_count" | "position";

const SEVERITY_ORDER: OffTargetSeverity[] = ["alto", "moderado", "leve", "sin_señal"];
const SEVERITY_ICON: Record<OffTargetSeverity, string> = {
  alto: "🔴",
  moderado: "🟠",
  leve: "🟡",
  sin_señal: "🟢",
};

/**
 * Tabla del Módulo 5: para cada candidato, cuántas coincidencias fuera de
 * blanco encontró BLAST en el transcriptoma humano, cuál fue la peor y qué
 * SEVERIDAD se le asignó (ver ADR 0006: ya no es un filtro binario --
 * ningún candidato se descarta acá, la severidad es insumo para el futuro
 * Módulo 7 de ranking).
 *
 * La severidad se calcula sobre el TRAMO SEGUIDO de bases apareadas sin
 * interrupción ("tramo seguido más largo"), no sobre el conteo de
 * mismatches: una diferencia en el medio del alineamiento parte la unión en
 * dos tramos débiles, mientras que la misma diferencia en el borde deja un
 * tramo largo intacto.
 */
export function OffTargetTable({ candidates }: Props) {
  const [severityFilter, setSeverityFilter] = useState<OffTargetSeverity | "todos">("todos");
  const [order, setOrder] = useState<OrderKey>("longest_perfect_run");
  const [expanded, setExpanded] = useState<number | null>(null);

  let rows =
    severityFilter === "todos"
      ? candidates
      : candidates.filter((c) => c.severity === severityFilter);
  rows = [...rows].sort((a, b) => {
    if (order === "longest_perfect_run") {
      return b.longest_perfect_run - a.longest_perfect_run;
    }
    if (order === "off_target_count") {
      return b.off_target_count - a.off_target_count;
    }
    return a.start - b.start;
  });

  const severityCounts = SEVERITY_ORDER.reduce<Record<string, number>>((acc, level) => {
    acc[level] = candidates.filter((c) => c.severity === level).length;
    return acc;
  }, {});

  return (
    <div className="card">
      <h2>
        <InfoTip text={glossary.offTarget}>Candidatos vs. off-target</InfoTip>
      </h2>
      <div className="controls-row">
        <label className="checkbox-row">
          <InfoTip text={glossary.offTargetSeverity}>Filtrar por severidad:</InfoTip>{" "}
          <select
            value={severityFilter}
            onChange={(e) =>
              setSeverityFilter(e.target.value as OffTargetSeverity | "todos")
            }
          >
            <option value="todos">Todos ({candidates.length})</option>
            {SEVERITY_ORDER.map((level) => (
              <option key={level} value={level}>
                {SEVERITY_ICON[level]} {level} ({severityCounts[level] ?? 0})
              </option>
            ))}
          </select>
        </label>
        <label className="checkbox-row">
          Ordenar por:{" "}
          <select
            value={order}
            onChange={(e) => setOrder(e.target.value as OrderKey)}
          >
            <option value="longest_perfect_run">Tramo seguido más largo</option>
            <option value="off_target_count">Cantidad de hits</option>
            <option value="position">Posición</option>
          </select>
        </label>
      </div>
      <p className="muted">
        Ningún candidato se descarta automáticamente por severidad de
        off-target (ver ADR 0006) -- es una señal para revisión / futuro
        ranking, no un filtro pasa/no-pasa.
      </p>

      <div className="table-scroll">
        <table className="candidates-table">
          <thead>
            <tr>
              <th>Posición</th>
              <th>Secuencia del parche (ASO)</th>
              <th>
                <InfoTip text={glossary.offTargetRule}>Hits off-target</InfoTip>
              </th>
              <th>Genes distintos afectados</th>
              <th>
                <InfoTip text={glossary.offTargetSeverity}>
                  Tramo seguido más largo
                </InfoTip>
              </th>
              <th>Peor coincidencia</th>
              <th>
                <InfoTip text={glossary.offTargetSeverity}>Severidad</InfoTip>
              </th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <Fragment key={c.start}>
                <tr>
                  <td className="mono">
                    {c.start}–{c.end}
                  </td>
                  <td className="mono">{c.aso_sequence}</td>
                  <td className="mono">{c.off_target_count}</td>
                  <td className="mono">{c.distinct_genes_hit}</td>
                  <td className="mono">
                    {c.longest_perfect_run > 0 ? `${c.longest_perfect_run} pb` : "—"}
                  </td>
                  <td>
                    {c.worst_hit ? (
                      <span className="mono">
                        {c.worst_hit.gene_symbol ?? c.worst_hit.transcript_id}{" "}
                        ({c.worst_hit.length} pb, {c.worst_hit.mismatches} mismatch
                        {c.worst_hit.mismatches === 1 ? "" : "es"})
                      </span>
                    ) : (
                      "— sin coincidencias relevantes"
                    )}
                  </td>
                  <td>
                    {SEVERITY_ICON[c.severity]} {c.severity_label}
                    {c.reasons.length > 0 && (
                      <span className="muted"> {c.reasons.join("; ")}</span>
                    )}
                  </td>
                  <td>
                    {c.hits.length > 0 && (
                      <button
                        type="button"
                        className="link-button"
                        onClick={() =>
                          setExpanded(expanded === c.start ? null : c.start)
                        }
                      >
                        {expanded === c.start ? "ocultar" : `ver ${c.hits.length}`}
                      </button>
                    )}
                  </td>
                </tr>
                {expanded === c.start && c.hits.length > 0 && (
                  <tr key={`${c.start}-detail`} className="row-detail">
                    <td colSpan={8}>
                      <table className="subtable">
                        <thead>
                          <tr>
                            <th>Transcrito</th>
                            <th>Gen</th>
                            <th>% identidad</th>
                            <th>Longitud</th>
                            <th>Mismatches</th>
                            <th>Tramo seguido</th>
                            <th>¿Es el gen blanco?</th>
                          </tr>
                        </thead>
                        <tbody>
                          {c.hits.map((h, i) => (
                            <tr key={i}>
                              <td className="mono">{h.transcript_id}</td>
                              <td className="mono">
                                {h.gene_symbol ?? h.gene_id ?? "—"}
                              </td>
                              <td className="mono">{h.pident.toFixed(1)}%</td>
                              <td className="mono">{h.length} pb</td>
                              <td className="mono">{h.mismatches}</td>
                              <td className="mono">{h.longest_perfect_run} pb</td>
                              <td>{h.is_target_gene ? "✅ ABCA4 (esperado)" : "⚠️ otro gen"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
