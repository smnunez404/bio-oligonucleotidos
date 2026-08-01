import { useState } from "react";
import type { AgreementResponse } from "../types";
import { InfoTip } from "./InfoTip";

interface Props {
  data: AgreementResponse;
}

/**
 * Concordancia entre SpliceAI y Pangolin, candidato por candidato (Módulo 6c
 * aplicado al 6b).
 *
 * El resultado que esta vista tiene que dejar claro NO es "concuerdan mucho",
 * sino que **la concordancia depende de qué se pregunte**: mirando un solo sitio
 * discrepan en 9 candidatos, y mirando el veredicto del pseudoexón coinciden en
 * todos. Esa brecha ES el hallazgo (ADR 0012), así que las dos cifras van juntas
 * y del mismo tamaño — mostrar solo el 100 % sería vender el resultado.
 *
 * Los 9 desacuerdos se listan con nombre. Un porcentaje sin los casos detrás no
 * se puede auditar.
 */
export function PredictorAgreement({ data }: Props) {
  const [openDetail, setOpenDetail] = useState(false);

  const pct = (v: number) => `${(v * 100).toFixed(1).replace(".", ",")} %`;

  return (
    <div className="card">
      <h2>
        ¿Un segundo predictor dice lo mismo?{" "}
        <InfoTip text="SpliceAI y Pangolin son dos redes neuronales entrenadas por grupos distintos, con arquitecturas distintas. Que coincidan hace mucho menos probable que el resultado sea un artefacto de una herramienta." />
      </h2>

      <div className="agreement-grid">
        <div className="agreement-metric agreement-metric-strong">
          <div className="agreement-number">
            {data.n_agree}/{data.n_compared}
          </div>
          <div className="agreement-label">
            coinciden en el <strong>veredicto</strong>
          </div>
          <p className="muted">
            ¿Desarma el pseudoexón sin romper el splicing sano? —{" "}
            {pct(data.agreement_fraction)}
          </p>
        </div>

        <div className="agreement-metric">
          <div className="agreement-number">
            {data.n_agree_by_site}/{data.n_compared}
          </div>
          <div className="agreement-label">
            coinciden mirando <strong>un solo sitio</strong>
          </div>
          <p className="muted">
            El criterio antiguo, solo el sitio de salida —{" "}
            {pct(data.agreement_fraction_by_site)}
          </p>
        </div>
      </div>

      <p>
        <strong>La diferencia entre esas dos cifras es el resultado</strong>, no
        un detalle: los {data.disagreements_by_site.length} candidatos en los que
        los predictores parecían discrepar son los que atacan el sitio de{" "}
        <em>entrada</em> del pseudoexón sin taparlo. El criterio que solo miraba
        el sitio de salida no los veía. Al preguntar lo que de verdad importa —
        si el pseudoexón queda desarmado — la discrepancia desaparece.
      </p>

      {data.disagreements_by_site.length > 0 && (
        <>
          <button
            type="button"
            className="link-button"
            onClick={() => setOpenDetail((v) => !v)}
          >
            {openDetail ? "Ocultar" : "Ver"} los{" "}
            {data.disagreements_by_site.length} casos, uno por uno
          </button>

          {openDetail && (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Candidato</th>
                  <th>Posición</th>
                  <th>SpliceAI (por sitio)</th>
                  <th>Pangolin (por sitio)</th>
                  <th>Veredicto de ambos</th>
                </tr>
              </thead>
              <tbody>
                {data.disagreements_by_site.map((c) => (
                  <tr key={c.name}>
                    <td>{c.name}</td>
                    <td>{c.start_rel}</td>
                    <td>{c.spliceai.classification}</td>
                    <td>{c.pangolin.classification}</td>
                    <td>
                      {c.agree ? "✅ " : "⚠️ "}
                      {c.spliceai.verdict}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}

      <p className="caveat">
        ⚠️ <strong>Hasta dónde vale:</strong> {data.limitation}
      </p>
    </div>
  );
}
