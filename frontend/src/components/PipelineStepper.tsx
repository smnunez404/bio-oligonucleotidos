interface Step {
  id: number;
  label: string;
  blurb: string;
}

const STEPS: Step[] = [
  { id: 1, label: "Secuencia", blurb: "Obtener el ADN/ARN con la mutación" },
  { id: 2, label: "Oligo-Walk", blurb: "Generar todos los parches candidatos" },
  { id: 3, label: "Filtros", blurb: "Descartar candidatos poco viables" },
  { id: 4, label: "Termodinámica", blurb: "¿Se pega bien y de forma estable?" },
  { id: 5, label: "Off-target", blurb: "¿Se pega en otro lugar por error?" },
  { id: 6, label: "Splicing", blurb: "¿Realmente corrige el error?" },
  { id: 7, label: "Ranking", blurb: "Elegir los mejores candidatos" },
];

export function PipelineStepper({ current }: { current: number }) {
  return (
    <div className="stepper card">
      <p className="stepper-title muted">El plan completo — en qué parte estamos</p>
      <div className="stepper-row">
        {STEPS.map((step, i) => {
          const state =
            step.id < current
              ? "done"
              : step.id === current
              ? "current"
              : "future";
          return (
            <div key={step.id} className="stepper-item-wrap">
              <div className={`stepper-item stepper-${state}`} title={step.blurb}>
                <span className="stepper-num">
                  {state === "done" ? "✓" : step.id}
                </span>
                <span className="stepper-label">{step.label}</span>
              </div>
              {i < STEPS.length - 1 && <span className="stepper-connector" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
