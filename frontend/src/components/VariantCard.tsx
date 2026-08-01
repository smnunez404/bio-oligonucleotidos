import type { VariantInfo, RegionInfo } from "../types";
import { InfoTip } from "./InfoTip";
import { glossary } from "../glossary";

interface Props {
  variant: VariantInfo;
  region: RegionInfo;
}

export function VariantCard({ variant, region }: Props) {
  return (
    <div className="card">
      <h2>
        <InfoTip text={glossary.gene}>{variant.gene}</InfoTip>{" "}
        <span className="hgvs">
          <InfoTip text={glossary.variantNotation}>{variant.hgvs_c}</InfoTip>
        </span>
      </h2>
      <dl className="fact-grid">
        <dt>
          <InfoTip text={glossary.transcript}>Transcrito</InfoTip>
        </dt>
        <dd>{variant.transcript} (MANE Select)</dd>

        <dt>
          <InfoTip text={glossary.genomicCoordinate}>
            Coordenada genómica (GRCh38)
          </InfoTip>
        </dt>
        <dd>{variant.hgvs_g_grch38}</dd>

        <dt>
          <InfoTip text={glossary.intron}>Ubicación</InfoTip>
        </dt>
        <dd>
          Intrón {variant.intron}, chr{variant.chromosome}:
          {variant.position_grch38.toLocaleString("es")}
        </dd>

        <dt>Ventana descargada</dt>
        <dd>
          chr{variant.chromosome}:{region.start_grch38.toLocaleString("es")}–
          {region.end_grch38.toLocaleString("es")} ({region.length.toLocaleString("es")} nt)
        </dd>

        <dt>Fuente</dt>
        <dd className="muted">{variant.source}</dd>
      </dl>
    </div>
  );
}
