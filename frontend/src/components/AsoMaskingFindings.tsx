import type { AsoMaskingResponse } from "../types";
import { InfoTip } from "./InfoTip";
import { glossary } from "../glossary";

interface Props {
  data: AsoMaskingResponse;
}

/**
 * Los tres hallazgos del Módulo 6b, en tarjetas separadas. Están arriba de la
 * tabla porque son la conclusión del módulo: la tabla es la evidencia, no el
 * mensaje.
 *
 * El tercero es una limitación de NUESTRO pipeline, no de la biología, y por eso
 * se muestra igual de visible que los otros dos.
 */
export function AsoMaskingFindings({ data }: Props) {
  const blockers = data.candidates.filter((c) => c.classification === "bloquea");
  const bad = data.candidates.filter((c) => c.classification === "contraproducente");
  const worst = [...bad].sort((a, b) => b.delta_donor - a.delta_donor)[0];

  return (
    <div className="findings-grid">
      <div className="card finding-card">
        <h3>1. Tapar una punta desarma el pseudoexón entero</h3>
        <p>
          Los {blockers.length} candidatos que tapan el sitio falso de salida lo
          llevan a <strong>0,0000</strong>. Lo interesante es que{" "}
          <em>también</em> hunden el sitio falso de entrada, que{" "}
          <strong>no tapan</strong>: baja de{" "}
          {data.baseline.acceptor_cryptic.toFixed(4)} a{" "}
          {Math.min(...blockers.map((c) => c.acceptor_cryptic)).toFixed(3)}–
          {Math.max(...blockers.map((c) => c.acceptor_cryptic)).toFixed(3)}.
        </p>
        <p className="muted">
          El predictor aprendió que los sitios de splicing{" "}
          <InfoTip text={glossary.crypticPair}>funcionan de a pares</InfoTip>. En
          la práctica: no hace falta tapar las dos puntas del trozo intruso.
          Tapando una, la otra deja de tener sentido.
        </p>
      </div>

      <div className="card finding-card finding-warn">
        <h3>2. {bad.length} de {data.total} candidatos empeorarían el problema</h3>
        <p>
          En vez de bajar la probabilidad del sitio falso, la{" "}
          <strong>suben</strong>. El peor ({worst?.name}) la lleva de{" "}
          {data.baseline.donor_cryptic.toFixed(4)} a{" "}
          <strong>{worst?.donor_cryptic.toFixed(4)}</strong> (
          {worst && worst.delta_donor >= 0 ? "+" : ""}
          {worst?.delta_donor.toFixed(4)}).
        </p>
        <p className="muted">
          Los módulos anteriores los dejaban pasar como equivalentes a
          cualquier otro, porque ordenan por propiedades físicas del oligo, que
          no tienen noción de{" "}
          <InfoTip text={glossary.counterproductive}>
            dirección del efecto
          </InfoTip>
          . Es el primer criterio de descarte biológico del proyecto.
        </p>
      </div>

      <div className="card finding-card finding-gap">
        <h3>3. Una de las dos dianas quedó sin candidatos</h3>
        <p>
          Ninguno de los {data.total} candidatos cubre el sitio falso de entrada
          (posición {data.sites.acceptor_cryptic_offset}). No es que no
          existieran: <strong>{data.acceptor_gap_note}</strong>
        </p>
        <p className="muted">
          Los filtros hicieron su trabajo — pero el resultado es que una diana
          quedó sin ninguna opción, y eso no era visible antes de este módulo.
          Según el hallazgo 1 quizás no importe; es una decisión a tomar, no un
          supuesto.
        </p>
      </div>
    </div>
  );
}
