import { InfoTip } from "./InfoTip";
import { glossary } from "../glossary";

interface Props {
  total: number;
  passed: number;
  rejected: number;
}

export function FilterSummary({ total, passed, rejected }: Props) {
  const passedPct = total > 0 ? (passed / total) * 100 : 0;

  return (
    <div className="card">
      <h2>
        <InfoTip text={glossary.passedFilter}>Resultado del filtro</InfoTip>
      </h2>
      <p className="muted">
        Reglas: <InfoTip text={glossary.gcContent}>GC% entre 40% y 70%</InfoTip>{" "}
        y sin <InfoTip text={glossary.gRun}>G-runs</InfoTip> (4+ G seguidas).
      </p>
      <div className="filter-bar">
        <div className="filter-bar-passed" style={{ width: `${passedPct}%` }} />
      </div>
      <div className="filter-stats">
        <span>
          ✅ <strong>{passed}</strong> aprobados
        </span>
        <span>
          ❌ <strong>{rejected}</strong> rechazados
        </span>
        <span className="muted">de {total} candidatos totales</span>
      </div>
    </div>
  );
}
