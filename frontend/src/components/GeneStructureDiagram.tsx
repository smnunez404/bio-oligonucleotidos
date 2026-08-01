import { InfoTip } from "./InfoTip";
import { glossary } from "../glossary";

/**
 * Esquema conceptual (no a escala) de qué pasa con el splicing del intrón 2
 * de ABCA4: normal (el intrón se recorta, los exones se pegan) vs. con la
 * mutación c.161-395G>A (un pedazo del intrón queda pegado por error =
 * pseudoexón). El tamaño exacto del pseudoexón todavía no está confirmado
 * (ver backlog del proyecto) — por eso este diagrama es ilustrativo, no una
 * medida exacta a escala.
 */
export function GeneStructureDiagram() {
  return (
    <div className="card">
      <h2>
        Qué le pasa al <InfoTip text={glossary.splicing}>splicing</InfoTip>{" "}
        (esquema conceptual)
      </h2>
      <p className="muted">
        No está a escala — es para entender el mecanismo, no las proporciones
        exactas. El tamaño real del{" "}
        <InfoTip text={glossary.pseudoexon}>pseudoexón</InfoTip> todavía es
        una pregunta abierta del proyecto.
      </p>

      <svg viewBox="0 0 720 300" className="gene-diagram" role="img">
        {/* fila normal */}
        <text x="10" y="24" className="diagram-row-label">
          ✅ Splicing normal
        </text>
        <g transform="translate(0, 40)">
          <rect x="20" y="0" width="90" height="36" rx="4" className="exon-box" />
          <text x="65" y="23" className="exon-label">Exón 2</text>

          <line x1="110" y1="18" x2="420" y2="18" className="intron-line" />
          <path
            d="M 130 18 Q 265 -30 400 18"
            className="loop-arc"
            fill="none"
          />
          <text x="265" y="-36" className="loop-label">se recorta y se descarta</text>

          <rect x="420" y="0" width="90" height="36" rx="4" className="exon-box" />
          <text x="465" y="23" className="exon-label">Exón 3</text>

          <text x="560" y="23" className="result-arrow">→</text>

          <rect x="590" y="0" width="120" height="36" rx="4" className="mrna-ok" />
          <text x="650" y="23" className="exon-label small">ARN correcto</text>
        </g>
        <text x="20" y="100" className="diagram-result-label ok">
          → proteína ABCA4 funcional
        </text>

        {/* fila mutante */}
        <text x="10" y="160" className="diagram-row-label">
          ❌ Splicing con la mutación c.161-395G&gt;A
        </text>
        <g transform="translate(0, 176)">
          <rect x="20" y="0" width="90" height="36" rx="4" className="exon-box" />
          <text x="65" y="23" className="exon-label">Exón 2</text>

          <line x1="110" y1="18" x2="200" y2="18" className="intron-line" />
          <rect x="200" y="0" width="70" height="36" rx="4" className="pseudoexon-box" />
          <text x="235" y="23" className="exon-label small">pseudoexón</text>
          <text x="235" y="-6" className="variant-pin">📍 mutación acá</text>
          <line x1="270" y1="18" x2="420" y2="18" className="intron-line" />

          <rect x="420" y="0" width="90" height="36" rx="4" className="exon-box" />
          <text x="465" y="23" className="exon-label">Exón 3</text>

          <text x="545" y="23" className="result-arrow">→</text>

          <rect x="575" y="0" width="145" height="36" rx="4" className="mrna-bad" />
          <text x="647" y="23" className="exon-label small">ARN con error</text>
        </g>
        <text x="20" y="266" className="diagram-result-label bad">
          → proteína truncada o degradada → pérdida de función
        </text>
      </svg>

      <p className="muted">
        El <InfoTip text={glossary.aso}>ASO</InfoTip> que vamos a diseñar
        (próximos módulos) actúa justo sobre la zona del pseudoexón: se pega
        ahí y tapa la señal que hace que el cuerpo lo confunda con un exón —
        el objetivo es volver a la fila de arriba (splicing normal).
      </p>
    </div>
  );
}
