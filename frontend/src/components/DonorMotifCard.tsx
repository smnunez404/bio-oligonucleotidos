import type { SpliceMotifsResponse } from "../types";
import { InfoTip } from "./InfoTip";
import { glossary } from "../glossary";

interface Props {
  data: SpliceMotifsResponse;
}

/** Muestra el motivo de 9 nt marcando qué posiciones coinciden con el consenso. */
function Motif({
  motif,
  matches,
  exonicLen,
}: {
  motif: string;
  matches: boolean[];
  exonicLen: number;
}) {
  return (
    <code className="motif">
      {motif.split("").map((base, i) => (
        <span key={i}>
          {i === exonicLen && <span className="motif-cut">|</span>}
          <span className={matches[i] ? "motif-hit" : "motif-miss"}>{base}</span>
        </span>
      ))}
    </code>
  );
}

export function DonorMotifCard({ data }: Props) {
  const top = data.candidates.find((c) => c.delta > 0);

  return (
    <div className="card">
      <h2>
        ¿Por qué justo esta letra? —{" "}
        <InfoTip text={glossary.donorSite}>sitio donador</InfoTip> críptico
      </h2>

      {top ? (
        <>
          <p className="intro-goal">
            La mutación refuerza una señal de corte latente que estaba justo al
            lado: pasa de coincidir en {top.wildtype_score} de 9 posiciones a
            coincidir en {top.mutant_score} de 9.
          </p>
          <p className="muted">
            Ese es exactamente el mecanismo esperado: un{" "}
            <InfoTip text={glossary.crypticSite}>sitio críptico</InfoTip> que
            la célula ignoraba se vuelve lo bastante fuerte como para que
            empiece a usarlo por error.
          </p>

          <div className="motif-block">
            <div className="motif-row">
              <span className="strand-label">Consenso ideal</span>
              <code className="motif motif-consensus">
                MAG<span className="motif-cut">|</span>GURAGU
              </code>
            </div>
            <div className="motif-row">
              <span className="strand-label">Wild-type</span>
              <Motif
                motif={top.wildtype_motif}
                matches={top.wildtype_matches}
                exonicLen={data.exonic_len}
              />
              <span className="motif-score">{top.wildtype_score}/9</span>
            </div>
            <div className="motif-row">
              <span className="strand-label">Mutante</span>
              <Motif
                motif={top.mutant_motif}
                matches={top.mutant_matches}
                exonicLen={data.exonic_len}
              />
              <span className="motif-score motif-score-up">
                {top.mutant_score}/9 ▲
              </span>
            </div>
          </div>

          <p className="muted">
            Verde = coincide con el consenso, gris = no coincide. La barra{" "}
            <code>|</code> marca dónde cortaría la célula. De{" "}
            {data.candidate_count} señales candidatas cerca de la mutación,{" "}
            <strong>solo {data.strengthened_count} se refuerza</strong> — y es
            justo la que toca la mutación.
          </p>
        </>
      ) : (
        <p className="muted">
          No se detectó ninguna señal de corte reforzada por la mutación en el
          radio analizado.
        </p>
      )}

      <p className="caveat">
        ⚠️ <strong>Cómo leer esto:</strong> es una{" "}
        <InfoTip text={glossary.consensusMatch}>
          comparación simple contra el consenso
        </InfoTip>
        , no un predictor entrenado — genera una hipótesis de dónde apuntar el
        parche, no una conclusión. El análisis serio (SpliceAI/Pangolin) es un
        módulo posterior. Además, la literatura reporta <em>tres</em>{" "}
        pseudoexones para esta variante; una sola señal reforzada no los
        explica todos.
      </p>
    </div>
  );
}
