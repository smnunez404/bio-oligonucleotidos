import type { AsoMaskingPredictor, PredictorId } from "../types";
import { InfoTip } from "./InfoTip";

interface Props {
  predictor: AsoMaskingPredictor;
  value: PredictorId;
  onChange: (p: PredictorId) => void;
  loading: boolean;
}

const LABELS: Record<PredictorId, string> = {
  spliceai: "SpliceAI",
  pangolin: "Pangolin",
};

/**
 * Selector de predictor para el Módulo 6b.
 *
 * El backend servía las dos corridas desde hace tiempo (`?predictor=`) pero la
 * interfaz mostraba solo SpliceAI, así que la revalidación con el segundo
 * predictor —el trabajo del Módulo 6c— era invisible salvo por API.
 *
 * Poder cambiar de predictor es didáctico además de completo: al alternar se ve
 * que los scores absolutos cambian mucho (los baselines son 0,5595 y 0,2829) y
 * que las conclusiones no. Eso hace tangible por qué el criterio tuvo que pasar
 * a ser relativo al baseline (ADR 0010).
 */
export function PredictorToggle({ predictor, value, onChange, loading }: Props) {
  return (
    <div className="card predictor-toggle">
      <div className="predictor-toggle-row">
        <span>
          <strong>Predictor:</strong>{" "}
          <InfoTip text="Dos redes neuronales distintas que predicen dónde la célula corta y pega el ARN. Fueron entrenadas por grupos diferentes, así que sirven para comprobarse mutuamente." />
        </span>
        {predictor.available.map((id) => {
          const pid = id as PredictorId;
          const active = pid === value;
          return (
            <button
              key={id}
              type="button"
              className={active ? "tab active" : "tab"}
              onClick={() => !active && onChange(pid)}
              disabled={loading}
            >
              {LABELS[pid] ?? id}
            </button>
          );
        })}
        {loading && <span className="muted">recalculando…</span>}
      </div>

      <p className="muted">
        Mostrando <strong>{predictor.label}</strong>. {predictor.note}.
      </p>
      <p className="muted">
        Al cambiar de predictor los números absolutos se mueven mucho — sus
        escalas están calibradas distinto — pero la clasificación casi no. Por eso
        el criterio de este módulo es la <strong>fracción de señal que el sitio
        retiene</strong>, y no una caída absoluta: un umbral en la escala de uno
        es inalcanzable en la del otro.
      </p>
    </div>
  );
}
