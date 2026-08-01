interface Fila {
  afirmacion: string;
  nivel: "solid" | "partial" | "unknown";
  etiqueta: string;
  nota: string;
}

const FILAS: Fila[] = [
  {
    afirmacion: "La mutación existe y sabemos su posición exacta",
    nivel: "solid",
    etiqueta: "✅ Verificado",
    nota: "Confirmado por dos vías independientes (VariantValidator + secuencia real de Ensembl). Además, la distancia calculada coincide exactamente con el nombre oficial de la variante.",
  },
  {
    afirmacion: "Dónde empieza y termina el intrón (1393 letras)",
    nivel: "solid",
    etiqueta: "✅ Verificado",
    nota: "Coordenadas reales de la base de datos oficial. El pipeline las usa para no diseñar parches que tapen zonas sanas.",
  },
  {
    afirmacion: "La mutación refuerza una señal de corte falsa",
    nivel: "partial",
    etiqueta: "🟡 Nuestro análisis",
    nota: "Lo calculamos nosotros y es coherente con lo que dice la literatura, pero es una regla de comparación simple. Falta confirmarlo con el análisis de IA (Módulo 6).",
  },
  {
    afirmacion: "Los números de termodinámica (fuerza de pegado, plegado)",
    nivel: "partial",
    etiqueta: "🟡 Aproximación",
    nota: "La química elegida (PMO) no tiene tablas publicadas. Usamos las más parecidas que existen. Sirven para comparar candidatos entre sí, no como valores absolutos.",
  },
  {
    afirmacion: "Dónde están exactamente los 3 pseudoexones",
    nivel: "unknown",
    etiqueta: "❌ No lo sabemos",
    nota: "Está en material suplementario de un paper que todavía no extrajimos. Por eso apuntamos alrededor de la mutación en vez de a los pseudoexones directamente.",
  },
  {
    afirmacion: "Que alguno de estos candidatos funcione de verdad",
    nivel: "unknown",
    etiqueta: "❌ Nadie lo sabe",
    nota: "No existe ningún parche publicado para esta mutación — somos los primeros mirando esto. Comprobarlo requiere laboratorio: sintetizar y probar en células.",
  },
];

export function EvidenceLevels() {
  return (
    <div className="card">
      <h2>Qué es firme y qué no</h2>
      <p className="muted">
        Separar esto es la parte más importante de una investigación honesta.
      </p>
      <table className="evidence-table">
        <tbody>
          {FILAS.map((f) => (
            <tr key={f.afirmacion}>
              <td>{f.afirmacion}</td>
              <td className={`evidence-badge ev-${f.nivel}`}>{f.etiqueta}</td>
              <td className="muted">{f.nota}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
