import type { AsoMaskingResponse } from "../types";

interface Props {
  data: AsoMaskingResponse;
}

/**
 * Panel de controles del Módulo 6b. Va ANTES de los resultados a propósito:
 * el método (tapar con N y volver a preguntar) no vale nada si no se
 * demuestra primero que hace lo que dice. Los cuatro controles se corrieron
 * antes de mirar los candidatos.
 *
 * El control decisivo es el último: tapar el sitio SANO del exón 3 debe
 * apagar ESE sitio y no el falso. Si tapar cualquier cosa hundiera todo,
 * estaríamos midiendo un artefacto del modelo, no un efecto real.
 */
export function AsoMaskingControls({ data }: Props) {
  const allOk = data.controls.every((c) => c.ok);

  return (
    <div className="card controls-card">
      <h2>Antes de los resultados: ¿el método funciona?</h2>
      <p>
        Tapar la secuencia con la letra <code>N</code> y volver a preguntarle al
        predictor solo sirve si se comporta como esperamos en casos donde ya
        sabemos la respuesta. Estos cuatro controles se corrieron{" "}
        <strong>antes</strong> de mirar un solo candidato.
      </p>

      <table className="data-table">
        <thead>
          <tr>
            <th>Control</th>
            <th>Qué esperábamos</th>
            <th>Sitio falso quedó en</th>
            <th>Cambio</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {data.controls.map((c) => (
            <tr key={c.name}>
              <td>{c.label}</td>
              <td className="muted">{c.expected}</td>
              <td>{c.donor_cryptic.toFixed(4)}</td>
              <td>
                {c.delta_donor >= 0 ? "+" : ""}
                {c.delta_donor.toFixed(4)}
              </td>
              <td>{c.ok ? "✅" : "❌"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className={allOk ? "controls-verdict-ok" : "controls-verdict-bad"}>
        {allOk
          ? "Los cuatro controles se comportaron como debían. El efecto que mide este módulo es local: tapar un sitio apaga ese sitio, no todos."
          : "Al menos un control falló. Los resultados de abajo NO son confiables hasta resolverlo."}
      </p>
    </div>
  );
}
