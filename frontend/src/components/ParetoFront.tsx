import type { RankingResponse } from "../types";
import { InfoTip } from "./InfoTip";

interface Props {
  data: RankingResponse;
  selected: string | null;
  onSelect: (name: string | null) => void;
}

const W = 720;
const H = 380;
const PAD = { top: 28, right: 24, bottom: 52, left: 62 };

/**
 * Dispersión bloqueo (X) vs. termodinámica (Y), con el tamaño del punto dando la
 * tercera dimensión (seguridad off-target). Los del frente de Pareto van
 * rellenos y con anillo; los dominados, huecos y apagados.
 *
 * Por qué esta vista y no un ranking en barras: un frente de Pareto NO es un
 * orden, es un conjunto de trade-offs. Una barra sugeriría que hay un primero y
 * un segundo, que es justamente lo que este módulo se niega a afirmar. La
 * dispersión hace visible la tensión real: los que más bloquean están abajo a la
 * derecha (peor termodinámica) y el mejor termodinámicamente está arriba a la
 * izquierda.
 */
export function ParetoFront({ data, selected, onSelect }: Props) {
  const pts = data.candidates;
  if (pts.length === 0) return null;

  const xs = pts.map((c) => c.objectives.block_strength);
  const ys = pts.map((c) => c.objectives.thermo_quality);
  const runs = pts.map((c) => c.raw.longest_perfect_run);

  // El eje X vive en un rango diminuto (0,944-1,000): sin margen propio los
  // puntos se apilarían contra el borde derecho.
  const xMin = Math.min(...xs) - 0.004;
  const xMax = Math.max(...xs) + 0.002;
  const yMin = 0;
  const yMax = Math.max(...ys) * 1.12;

  const runMin = Math.min(...runs);
  const runMax = Math.max(...runs);

  const px = (v: number) =>
    PAD.left + ((v - xMin) / (xMax - xMin)) * (W - PAD.left - PAD.right);
  const py = (v: number) =>
    H - PAD.bottom - ((v - yMin) / (yMax - yMin)) * (H - PAD.top - PAD.bottom);
  // Menos homología contigua = más seguro = punto más grande.
  const pr = (run: number) =>
    runMax === runMin ? 9 : 13 - ((run - runMin) / (runMax - runMin)) * 6;

  const xTicks = 4;
  const yTicks = 4;

  return (
    <div className="card">
      <h2>
        El frente de Pareto{" "}
        <InfoTip text="Los candidatos que ningún otro supera en las tres dimensiones a la vez. No es un orden del 1 al 10: es el conjunto de los que representan un trade-off distinto, sin que se pueda decir cuál es mejor sin decidir qué se prioriza." />
      </h2>
      <p className="muted">
        Cada círculo es un candidato. <strong>Horizontal:</strong> fuerza de
        bloqueo. <strong>Vertical:</strong> calidad termodinámica.{" "}
        <strong>Tamaño:</strong> seguridad off-target (más grande = menos
        homología con otros genes). Los <strong>rellenos con borde</strong> son
        los {data.front.length} del frente.
      </p>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        style={{ width: "100%", height: "auto", maxWidth: W }}
        role="img"
        aria-label={`Dispersión de ${pts.length} candidatos; ${data.front.length} en el frente de Pareto`}
      >
        {/* rejilla + ejes */}
        {Array.from({ length: yTicks + 1 }, (_, i) => {
          const v = yMin + ((yMax - yMin) * i) / yTicks;
          return (
            <g key={`y${i}`}>
              <line
                x1={PAD.left}
                x2={W - PAD.right}
                y1={py(v)}
                y2={py(v)}
                stroke="#e5e7eb"
                strokeWidth={1}
              />
              <text x={PAD.left - 8} y={py(v) + 4} textAnchor="end" fontSize={11} fill="#6b7280">
                {v.toFixed(0)}
              </text>
            </g>
          );
        })}
        {Array.from({ length: xTicks + 1 }, (_, i) => {
          const v = xMin + ((xMax - xMin) * i) / xTicks;
          return (
            <text
              key={`x${i}`}
              x={px(v)}
              y={H - PAD.bottom + 18}
              textAnchor="middle"
              fontSize={11}
              fill="#6b7280"
            >
              {v.toFixed(3)}
            </text>
          );
        })}

        <line
          x1={PAD.left}
          x2={W - PAD.right}
          y1={H - PAD.bottom}
          y2={H - PAD.bottom}
          stroke="#9ca3af"
        />
        <line x1={PAD.left} x2={PAD.left} y1={PAD.top} y2={H - PAD.bottom} stroke="#9ca3af" />

        <text
          x={(PAD.left + W - PAD.right) / 2}
          y={H - 10}
          textAnchor="middle"
          fontSize={12}
          fill="#374151"
        >
          Fuerza de bloqueo (1 = el sitio falso queda totalmente apagado)
        </text>
        <text
          x={-(PAD.top + H - PAD.bottom) / 2}
          y={15}
          transform="rotate(-90)"
          textAnchor="middle"
          fontSize={12}
          fill="#374151"
        >
          Calidad termodinámica (percentil)
        </text>

        {/* puntos: primero los dominados, para que el frente quede encima */}
        {[...pts]
          .sort((a, b) => Number(a.in_front) - Number(b.in_front))
          .map((c) => {
            const isSel = selected === c.name;
            const x = px(c.objectives.block_strength);
            const y = py(c.objectives.thermo_quality);
            const r = pr(c.raw.longest_perfect_run);
            return (
              <g
                key={c.name}
                onClick={() => onSelect(isSel ? null : c.name)}
                style={{ cursor: "pointer" }}
              >
                <title>
                  {`${c.name}\nbloqueo ${c.objectives.block_strength.toFixed(5)}\n` +
                    `termodinámica ${c.objectives.thermo_quality.toFixed(1)}\n` +
                    `tramo off-target ${c.raw.longest_perfect_run} pb\n` +
                    `anula: ${c.borders_abolished.join(" + ") || "—"}\n` +
                    (c.in_front ? "EN EL FRENTE" : `dominado por ${c.dominated_by.join(", ")}`)}
                </title>
                <circle
                  cx={x}
                  cy={y}
                  r={r}
                  fill={c.in_front ? "#0d9488" : "#ffffff"}
                  stroke={isSel ? "#b45309" : c.in_front ? "#0f766e" : "#9ca3af"}
                  strokeWidth={isSel ? 3.5 : c.in_front ? 2.5 : 1.5}
                  opacity={c.in_front ? 0.9 : 0.75}
                />
                {c.in_front && (
                  <text
                    x={x}
                    y={y - r - 6}
                    textAnchor="middle"
                    fontSize={11}
                    fontWeight={600}
                    fill="#0f766e"
                  >
                    {c.name.replace("cand_", "")}
                  </text>
                )}
              </g>
            );
          })}
      </svg>

      <p className="caveat">
        ⚠️ Los tres del frente <strong>no están empatados ni ordenados</strong>:
        cada uno gana en algo distinto. Elegir entre ellos es una decisión de
        criterio sobre qué se prioriza, no un resultado que el pipeline pueda
        calcular.
      </p>
    </div>
  );
}
