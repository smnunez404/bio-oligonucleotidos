import type { OligoCandidate } from "../types";
import { InfoTip } from "./InfoTip";
import { glossary } from "../glossary";

interface Props {
  candidates: OligoCandidate[];
  scanStart: number;
  scanEnd: number;
  variantOffset: number;
}

const SAMPLE_COUNT = 16;
const SVG_WIDTH = 680;
const ROW_HEIGHT = 16;
const TOP_MARGIN = 30;

/** Muestra una selección espaciada de candidatos como "pistas" apiladas (estilo genome browser), para dar intuición visual del Oligo-Walk sin renderizar los 300+ candidatos completos. */
export function OligoWalkTrack({ candidates, scanStart, scanEnd, variantOffset }: Props) {
  const span = scanEnd - scanStart || 1;
  const xFor = (pos: number) => ((pos - scanStart) / span) * SVG_WIDTH;

  const stepBetweenSamples = Math.max(1, Math.floor(candidates.length / SAMPLE_COUNT));
  const sampled = candidates.filter((_, i) => i % stepBetweenSamples === 0).slice(0, SAMPLE_COUNT);

  const height = TOP_MARGIN + sampled.length * ROW_HEIGHT + 10;
  const variantX = xFor(variantOffset);

  return (
    <div className="card">
      <h2>
        <InfoTip text={glossary.slidingWindow}>Ventana deslizante</InfoTip> —
        vista previa
      </h2>
      <p className="muted">
        {sampled.length} de {candidates.length} candidatos, espaciados para
        que se vea el patrón (no se renderizan todos). La línea punteada roja
        marca la mutación.
      </p>
      <svg viewBox={`0 0 ${SVG_WIDTH} ${height}`} className="oligo-track" role="img">
        <line
          x1={variantX}
          y1={0}
          x2={variantX}
          y2={height}
          className="track-variant-line"
        />
        <text x={variantX} y={12} className="track-variant-label" textAnchor="middle">
          variante
        </text>

        {sampled.map((c, i) => {
          const x1 = xFor(c.start);
          const x2 = xFor(c.end);
          return (
            <g key={c.start} transform={`translate(0, ${TOP_MARGIN + i * ROW_HEIGHT})`}>
              <rect
                x={x1}
                y={0}
                width={Math.max(2, x2 - x1)}
                height={ROW_HEIGHT - 4}
                rx={2}
                className={c.covers_variant ? "track-bar covers" : "track-bar"}
              />
            </g>
          );
        })}
      </svg>
    </div>
  );
}
