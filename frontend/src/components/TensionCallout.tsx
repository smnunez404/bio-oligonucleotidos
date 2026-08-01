import type { ThermoCandidate } from "../types";

interface Props {
  candidates: ThermoCandidate[];
  donorRange: [number, number];
}

/**
 * Señala una tensión real encontrada en los datos: los candidatos con la diana
 * más accesible NO son los que cubren el sitio donador críptico. Es una
 * decisión que el ranking final (Módulo 7) tendrá que resolver explícitamente,
 * así que conviene que esté visible desde ahora y no enterrada en una tabla.
 */
export function TensionCallout({ candidates, donorRange }: Props) {
  const aprobados = candidates.filter((c) => c.passed);
  if (aprobados.length === 0) return null;

  const sobreDonador = aprobados.filter(
    (c) => c.start < donorRange[1] && c.end > donorRange[0]
  );
  const masAccesible = [...aprobados].sort(
    (a, b) => (b.accessibility_percentile ?? -1) - (a.accessibility_percentile ?? -1)
  )[0];

  if (sobreDonador.length === 0 || !masAccesible) return null;

  const mejorSobreDonador = [...sobreDonador].sort(
    (a, b) => (b.accessibility_percentile ?? -1) - (a.accessibility_percentile ?? -1)
  )[0];

  return (
    <div className="card tension-card">
      <h2>⚖️ Una tensión que habrá que resolver</h2>
      <p>
        Los datos muestran dos grupos de buenos candidatos que{" "}
        <strong>no coinciden</strong>:
      </p>
      <div className="tension-grid">
        <div className="tension-side">
          <div className="tension-title">Los más accesibles</div>
          <div className="tension-value mono">
            {masAccesible.start}–{masAccesible.end}
          </div>
          <div className="muted">
            accesibilidad p
            {masAccesible.accessibility_percentile?.toFixed(0)} — la diana está
            muy expuesta, el parche llega fácil…
          </div>
          <div className="tension-bad">
            …pero está a {Math.abs(masAccesible.distance_to_variant)} nt de la
            mutación, lejos del sitio que causa el problema.
          </div>
        </div>
        <div className="tension-side">
          <div className="tension-title">Los que tapan el sitio crítico</div>
          <div className="tension-value mono">
            {mejorSobreDonador.start}–{mejorSobreDonador.end}
          </div>
          <div className="muted">
            cubren el sitio donador críptico que la mutación refuerza — atacan
            la causa directa…
          </div>
          <div className="tension-bad">
            …pero su accesibilidad es baja (p
            {mejorSobreDonador.accessibility_percentile?.toFixed(0)}): esa zona
            del ARN está más plegada.
          </div>
        </div>
      </div>
      <p className="muted">
        Solo <strong>{sobreDonador.length}</strong> de los{" "}
        {aprobados.length} candidatos aprobados cubren el sitio donador. La
        decisión de cómo pesar "accesible" contra "en el lugar correcto" es
        justamente lo que hará el módulo de ranking final — y es una decisión
        de criterio, no algo que los datos resuelvan solos.
      </p>
    </div>
  );
}
