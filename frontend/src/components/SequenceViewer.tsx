import type { ComparisonInfo } from "../types";
import { InfoTip } from "./InfoTip";
import { glossary } from "../glossary";

interface Props {
  comparison: ComparisonInfo;
}

/** Renderiza una secuencia como monospace, resaltando el nt en `highlightIndex`. */
function Strand({
  label,
  seq,
  highlightIndex,
  highlightClass,
}: {
  label: string;
  seq: string;
  highlightIndex: number;
  highlightClass: string;
}) {
  return (
    <div className="strand-row">
      <span className="strand-label">{label}</span>
      <code className="strand-seq">
        {seq.slice(0, highlightIndex)}
        <span className={highlightClass}>{seq[highlightIndex]}</span>
        {seq.slice(highlightIndex + 1)}
      </code>
    </div>
  );
}

export function SequenceViewer({ comparison }: Props) {
  const { wildtype, mutant, variant_offset_in_context: v } = comparison;

  return (
    <div className="card">
      <h2>Secuencia (sentido del transcrito)</h2>
      <p className="muted">
        ±{comparison.context_nt} nt alrededor de la variante. La{" "}
        <InfoTip text={glossary.variantBase}>base resaltada</InfoTip> es la
        posición exacta de c.161-395G&gt;A.
      </p>
      <div className="strand-block">
        <Strand
          label="Wild-type"
          seq={wildtype}
          highlightIndex={v}
          highlightClass="base-wt"
        />
        <Strand
          label="Mutante"
          seq={mutant}
          highlightIndex={v}
          highlightClass="base-mut"
        />
      </div>
      <div className="legend">
        <span className="legend-item">
          <span className="swatch base-wt" />
          <InfoTip text={glossary.wildtype}>alelo de referencia (G)</InfoTip>
        </span>
        <span className="legend-item">
          <span className="swatch base-mut" />
          <InfoTip text={glossary.mutant}>alelo mutante (A)</InfoTip>
        </span>
      </div>
    </div>
  );
}
