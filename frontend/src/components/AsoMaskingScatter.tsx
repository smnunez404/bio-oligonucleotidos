import { useState } from "react";
import type { AsoMaskingCandidate, AsoMaskingResponse } from "../types";
import { InfoTip } from "./InfoTip";
import { glossary } from "../glossary";

interface Props {
  data: AsoMaskingResponse;
  selected: string | null;
  onSelect: (name: string | null) => void;
}

const SVG_W = 680;
const SVG_H = 300;
const PAD_L = 52;
const PAD_R = 12;
const PAD_T = 18;
const PAD_B = 38;

const X_MIN = -200;
const X_MAX = 200;
const Y_MIN = -0.65;
const Y_MAX = 0.30;

const CLASS_COLOR: Record<string, string> = {
  bloquea: "#c0392b",
  contraproducente: "#e67e22",
  sin_efecto: "#95a5a6",
};

/**
 * Dispersión del Módulo 6b: una marca por candidato, ubicada en la posición
 * donde el ASO se pega (eje X) y en cuánto movió la probabilidad del sitio
 * falso (eje Y).
 *
 * Se lee de arriba hacia abajo: los de arriba EMPEORAN el problema, los del
 * medio no hacen nada, los de abajo lo apagan. La lectura clave es que solo
 * los que caen encima de la línea roja (el sitio falso) llegan a la banda
 * verde -- el efecto es local, no difuso.
 */
export function AsoMaskingScatter({ data, selected, onSelect }: Props) {
  const [hover, setHover] = useState<AsoMaskingCandidate | null>(null);

  const xFor = (v: number) => PAD_L + ((v - X_MIN) / (X_MAX - X_MIN)) * (SVG_W - PAD_L - PAD_R);
  const yFor = (v: number) => PAD_T + ((Y_MAX - v) / (Y_MAX - Y_MIN)) * (SVG_H - PAD_T - PAD_B);

  const centerOf = (c: AsoMaskingCandidate) => (c.start_rel + c.end_rel) / 2;

  // Los umbrales de la API son RELATIVOS al baseline (fracción de señal
  // retenida, ADR 0010), porque un umbral absoluto no es transferible entre
  // predictores: -0,43 es inalcanzable en la escala de Pangolin. Este gráfico
  // dibuja deltas absolutos, así que se convierten con el baseline de ESTA
  // corrida -- y así las bandas se reubican solas al cambiar de predictor.
  const baseDonor = data.baseline.donor_cryptic;
  const blockDelta = baseDonor * (data.thresholds.block_retention - 1);
  const badDelta = baseDonor * data.thresholds.counterproductive_gain;

  const blockY = yFor(blockDelta);
  const badY = yFor(badDelta);
  const zeroY = yFor(0);
  const donorX = xFor(data.sites.donor_cryptic_offset);
  const acceptorX = xFor(data.sites.acceptor_cryptic_offset);

  const shown = hover ?? data.candidates.find((c) => c.name === selected) ?? null;

  return (
    <div className="card">
      <h2>
        ¿Cada parche apaga o enciende el{" "}
        <InfoTip text={glossary.crypticPair}>sitio falso</InfoTip>?
      </h2>
      <p className="muted">
        Cada punto es uno de los {data.total} candidatos. Eje horizontal: dónde
        se pega, contado desde la mutación. Eje vertical: cuánto cambió la
        probabilidad del sitio falso al taparlo. Pasá el mouse por un punto para
        ver sus números, o hacé clic para resaltarlo en la tabla.
      </p>

      <svg viewBox={`0 0 ${SVG_W} ${SVG_H}`} className="aso-mask-scatter" role="img">
        {/* bandas de decisión */}
        <rect x={PAD_L} y={blockY} width={SVG_W - PAD_L - PAD_R} height={SVG_H - PAD_B - blockY}
              fill="#d5f5e3" />
        <rect x={PAD_L} y={PAD_T} width={SVG_W - PAD_L - PAD_R} height={badY - PAD_T}
              fill="#fdebd0" />
        <text x={PAD_L + 6} y={SVG_H - PAD_B - 8} fontSize="10" fill="#1e8449">
          apaga el sitio falso (≤ {blockDelta.toFixed(2)})
        </text>
        <text x={PAD_L + 6} y={PAD_T + 12} fontSize="10" fill="#b9770e">
          lo empeora (≥ +{badDelta.toFixed(2)})
        </text>

        {/* ejes */}
        <line x1={PAD_L} y1={zeroY} x2={SVG_W - PAD_R} y2={zeroY} stroke="#2c3e50" strokeWidth="1" />
        <line x1={PAD_L} y1={PAD_T} x2={PAD_L} y2={SVG_H - PAD_B} stroke="#7f8c8d" strokeWidth="1" />

        {/* sitios crípticos */}
        <line x1={donorX} y1={PAD_T} x2={donorX} y2={SVG_H - PAD_B}
              stroke="#c0392b" strokeWidth="1.2" strokeDasharray="4 3" />
        <text x={donorX + 4} y={PAD_T + 26} fontSize="9.5" fill="#c0392b">
          sitio falso de salida (+{data.sites.donor_cryptic_offset})
        </text>
        <line x1={acceptorX} y1={PAD_T} x2={acceptorX} y2={SVG_H - PAD_B}
              stroke="#2980b9" strokeWidth="1.2" strokeDasharray="4 3" />
        <text x={acceptorX + 4} y={PAD_T + 40} fontSize="9.5" fill="#2980b9">
          sitio falso de entrada ({data.sites.acceptor_cryptic_offset})
        </text>

        {/* marcas del eje Y */}
        {[0.2, 0, -0.2, -0.4, -0.6].map((v) => (
          <g key={v}>
            <text x={PAD_L - 6} y={yFor(v) + 3} fontSize="9" fill="#7f8c8d" textAnchor="end">
              {v > 0 ? `+${v.toFixed(1)}` : v.toFixed(1)}
            </text>
          </g>
        ))}
        {/* marcas del eje X */}
        {[-150, -100, -50, 0, 50, 100, 150].map((v) => (
          <g key={v}>
            <text x={xFor(v)} y={SVG_H - PAD_B + 14} fontSize="9" fill="#7f8c8d" textAnchor="middle">
              {v}
            </text>
          </g>
        ))}
        <text x={(SVG_W + PAD_L) / 2} y={SVG_H - 6} fontSize="10" fill="#2c3e50" textAnchor="middle">
          posición del parche, contada desde la mutación (nt)
        </text>

        {/* puntos */}
        {data.candidates.map((c) => {
          const isSel = c.name === selected;
          return (
            <circle
              key={c.name}
              cx={xFor(centerOf(c))}
              cy={yFor(c.delta_donor)}
              r={isSel ? 7 : 4.6}
              fill={CLASS_COLOR[c.classification]}
              stroke={isSel ? "#2c3e50" : "white"}
              strokeWidth={isSel ? 2 : 0.8}
              style={{ cursor: "pointer" }}
              onMouseEnter={() => setHover(c)}
              onMouseLeave={() => setHover(null)}
              onClick={() => onSelect(isSel ? null : c.name)}
            />
          );
        })}
      </svg>

      {shown ? (
        <div className="aso-mask-tooltip">
          <strong>{shown.name}</strong> — se pega entre {shown.start_rel} y{" "}
          {shown.end_rel} (contado desde la mutación).{" "}
          {shown.covers_donor ? "Tapa el sitio falso de salida." : "No lo tapa."}
          <ul>
            <li>
              sitio falso de salida: {data.baseline.donor_cryptic.toFixed(4)} →{" "}
              <strong>{shown.donor_cryptic.toFixed(4)}</strong> (
              {shown.delta_donor >= 0 ? "+" : ""}
              {shown.delta_donor.toFixed(4)})
            </li>
            <li>
              sitio falso de entrada: {data.baseline.acceptor_cryptic.toFixed(4)} →{" "}
              {shown.acceptor_cryptic.toFixed(4)} (
              {shown.delta_acceptor >= 0 ? "+" : ""}
              {shown.delta_acceptor.toFixed(4)})
            </li>
            <li>
              sitio sano del exón 3: cambió{" "}
              {shown.delta_canonical >= 0 ? "+" : ""}
              {shown.delta_canonical.toFixed(4)} (no se toca)
            </li>
          </ul>
        </div>
      ) : (
        <p className="muted aso-mask-hint">
          Sin selección. Los tres puntos rojos, sobre la línea roja, son los
          únicos que llegan a la banda verde.
        </p>
      )}
    </div>
  );
}
