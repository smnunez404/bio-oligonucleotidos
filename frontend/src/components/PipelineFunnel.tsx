interface Props {
  generated: number;
  passedHeuristic: number;
  passedThermo: number;
  /**
   * Opcional: si se pasa, agrega la etapa del Módulo 5 (off-target) al
   * embudo. Desde ADR 0006 el Módulo 5 ya NO descarta candidatos -- este
   * número es cuántos quedaron ANOTADOS con severidad, no cuántos "pasaron".
   */
  annotatedOffTarget?: number;
}

/** Embudo visual: cuántos candidatos sobreviven cada etapa del pipeline. */
export function PipelineFunnel({
  generated,
  passedHeuristic,
  passedThermo,
  annotatedOffTarget,
}: Props) {
  const etapas = [
    { label: "Generados (Oligo-Walk)", n: generated, color: "var(--border)" },
    { label: "Pasan filtro rápido", n: passedHeuristic, color: "var(--accent)" },
    { label: "Pasan termodinámica", n: passedThermo, color: "#2ecc71" },
    ...(annotatedOffTarget !== undefined
      ? [{ label: "Anotados con severidad off-target", n: annotatedOffTarget, color: "#f1c40f" }]
      : []),
  ];

  return (
    <div className="card">
      <h2>Embudo del pipeline</h2>
      <p className="muted">
        Cada etapa descarta candidatos inviables. La idea es gastar el cómputo
        caro solo en los que sobrevivieron a los filtros baratos.
      </p>
      <div className="funnel">
        {etapas.map((e) => (
          <div className="funnel-step" key={e.label}>
            <div className="funnel-label">{e.label}</div>
            <div className="funnel-track">
              <div
                className="funnel-fill"
                style={{
                  width: `${(e.n / generated) * 100}%`,
                  background: e.color,
                }}
              />
            </div>
            <div className="funnel-count">{e.n}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
