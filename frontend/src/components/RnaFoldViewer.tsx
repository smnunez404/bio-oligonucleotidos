import { useMemo, useState } from "react";
import type { StructureResponse } from "../types";
import { InfoTip } from "./InfoTip";
import { glossary } from "../glossary";

interface Props {
  data: StructureResponse;
}

/** Empareja índices a partir de la notación dot-bracket. */
function parsePairs(structure: string): [number, number][] {
  const stack: number[] = [];
  const pairs: [number, number][] = [];
  for (let i = 0; i < structure.length; i++) {
    if (structure[i] === "(") stack.push(i);
    else if (structure[i] === ")") {
      const j = stack.pop();
      if (j !== undefined) pairs.push([j, i]);
    }
  }
  return pairs;
}

/** Escala de color: enterrado (azul oscuro) -> expuesto (amarillo). */
function accessibilityColor(u: number | null): string {
  if (u === null) return "#555";
  const t = Math.min(1, Math.max(0, u));
  // interpolación azul oscuro -> cian -> amarillo
  if (t < 0.5) {
    const k = t / 0.5;
    const r = Math.round(30 + k * 0);
    const g = Math.round(50 + k * 150);
    const b = Math.round(110 + k * 90);
    return `rgb(${r},${g},${b})`;
  }
  const k = (t - 0.5) / 0.5;
  const r = Math.round(30 + k * 220);
  const g = Math.round(200 + k * 20);
  const b = Math.round(200 - k * 160);
  return `rgb(${r},${g},${b})`;
}

type Region = {
  key: string;
  label: string;
  from: number;
  to: number;
  color: string;
};

export function RnaFoldViewer({ data }: Props) {
  const [hovered, setHovered] = useState<Region | null>(null);

  const pairs = useMemo(() => parsePairs(data.structure), [data.structure]);

  const { minX, minY, width, height } = useMemo(() => {
    const xs = data.points.map((p) => p.x);
    const ys = data.points.map((p) => p.y);
    const pad = 30;
    const mnX = Math.min(...xs) - pad;
    const mnY = Math.min(...ys) - pad;
    return {
      minX: mnX,
      minY: mnY,
      width: Math.max(...xs) - mnX + pad,
      height: Math.max(...ys) - mnY + pad,
    };
  }, [data.points]);

  // Las posiciones de los candidatos son absolutas; la estructura es relativa a la ventana.
  const toLocal = (abs: number) => abs - data.window.start;

  const regions: Region[] = [];
  if (data.donor_range) {
    regions.push({
      key: "donor",
      label: "Señal falsa que causa el problema",
      from: toLocal(data.donor_range.start),
      to: toLocal(data.donor_range.end),
      color: "#e5484d",
    });
  }
  if (data.donor_covering.length > 0) {
    const c = data.donor_covering[0];
    regions.push({
      key: "covering",
      label: `Parche que SÍ tapa la señal (accesibilidad p${c.accessibility_percentile?.toFixed(0)})`,
      from: toLocal(c.start),
      to: toLocal(c.end),
      color: "#f5a524",
    });
  }
  if (data.most_accessible) {
    const m = data.most_accessible;
    regions.push({
      key: "accessible",
      label: `Parche más alcanzable (p${m.accessibility_percentile?.toFixed(0)}, pero a ${Math.abs(m.distance_to_variant)} nt del problema)`,
      from: toLocal(m.start),
      to: toLocal(m.end),
      color: "#2ecc71",
    });
  }

  const pointAt = (i: number) => data.points[i];
  const inWindow = (i: number) => i >= 0 && i < data.points.length;

  return (
    <div className="card">
      <h2>El ARN real, plegado — por qué no se puede llegar a cualquier lado</h2>
      <p className="muted">
        Esto <strong>no es un dibujo genérico</strong>: es el plegado calculado
        de esta secuencia concreta (
        <InfoTip text={glossary.mfe}>MFE {data.mfe} kcal/mol</InfoTip>). El{" "}
        <strong>{Math.round(data.paired_fraction * 100)}% de las bases está
        apareada</strong> — o sea, el "papel" está arrugado sobre sí mismo, y
        eso decide qué zonas se pueden alcanzar.
      </p>

      <svg
        viewBox={`${minX} ${minY} ${width} ${height}`}
        className="rna-fold"
        role="img"
      >
        {/* pares de bases */}
        {pairs.map(([i, j]) => (
          <line
            key={`p${i}-${j}`}
            x1={pointAt(i).x}
            y1={pointAt(i).y}
            x2={pointAt(j).x}
            y2={pointAt(j).y}
            className="rna-pair"
          />
        ))}

        {/* esqueleto */}
        <polyline
          points={data.points.map((p) => `${p.x},${p.y}`).join(" ")}
          className="rna-backbone"
        />

        {/* nucleótidos coloreados por accesibilidad */}
        {data.points.map((p) => (
          <circle
            key={p.i}
            cx={p.x}
            cy={p.y}
            r={3.2}
            fill={accessibilityColor(p.u)}
          />
        ))}

        {/* regiones destacadas */}
        {regions.map((r) => {
          const pts = [];
          for (let i = r.from; i < r.to; i++) {
            if (inWindow(i)) pts.push(`${pointAt(i).x},${pointAt(i).y}`);
          }
          if (pts.length === 0) return null;
          const dim = hovered !== null && hovered.key !== r.key;
          return (
            <polyline
              key={r.key}
              points={pts.join(" ")}
              className="rna-region"
              stroke={r.color}
              opacity={dim ? 0.2 : 1}
              onMouseEnter={() => setHovered(r)}
              onMouseLeave={() => setHovered(null)}
            />
          );
        })}

        {/* la mutación */}
        {inWindow(data.variant_index) && (
          <>
            <circle
              cx={pointAt(data.variant_index).x}
              cy={pointAt(data.variant_index).y}
              r={9}
              className="rna-variant-halo"
            />
            <circle
              cx={pointAt(data.variant_index).x}
              cy={pointAt(data.variant_index).y}
              r={4.5}
              className="rna-variant-dot"
            />
          </>
        )}
      </svg>

      <div className="rna-legend">
        {regions.map((r) => (
          <span
            key={r.key}
            className="legend-item rna-legend-item"
            onMouseEnter={() => setHovered(r)}
            onMouseLeave={() => setHovered(null)}
          >
            <span className="swatch" style={{ background: r.color }} />
            {r.label}
          </span>
        ))}
        <span className="legend-item">
          <span className="swatch rna-variant-swatch" /> la mutación
        </span>
      </div>

      <div className="rna-scale">
        <span className="muted">Color de cada base:</span>
        <span className="rna-gradient" />
        <span className="muted">
          enterrada (no se llega) → expuesta (alcanzable)
        </span>
      </div>

      <p className="caveat">
        ⚠️ Es un <strong>modelo</strong>, no una fotografía: es el plegado de
        mínima energía calculado sobre una ventana aislada. En una célula real
        el ARN se mueve, tiene proteínas pegadas y el contexto es más largo.
        Sirve para entender el problema y comparar candidatos entre sí, no como
        una imagen literal de lo que pasa dentro del ojo.
      </p>
    </div>
  );
}
