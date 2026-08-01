interface Props {
  title: string;
  goal: string;
  detail: string;
}

/** Tarjeta breve al inicio de cada vista: qué es, para qué sirve, qué mirar. */
export function ModuleIntro({ title, goal, detail }: Props) {
  return (
    <div className="card intro-card">
      <h2>{title}</h2>
      <p className="intro-goal">{goal}</p>
      <p className="muted">{detail}</p>
    </div>
  );
}
