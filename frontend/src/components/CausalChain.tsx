import { useState } from "react";

interface Paso {
  icono: string;
  titulo: string;
  detalle: string;
}

const PASOS: Paso[] = [
  {
    icono: "🧬",
    titulo: "El gen ABCA4",
    detalle:
      "Es el 'manual de instrucciones' para fabricar una pieza concreta. Vive en el ADN de todas tus células.",
  },
  {
    icono: "🔧",
    titulo: "La proteína ABCA4",
    detalle:
      "La pieza fabricada. Trabaja en la retina y su función es sacar la basura: bombea afuera un residuo que se genera cada vez que tus ojos captan luz.",
  },
  {
    icono: "🗑️",
    titulo: "El residuo se acumula",
    detalle:
      "Si la pieza no funciona, el residuo se queda adentro y se transforma en compuestos tóxicos que se van juntando en el tejido de la retina.",
  },
  {
    icono: "💀",
    titulo: "Mueren las células de la visión",
    detalle:
      "La acumulación tóxica daña el tejido y las células que detectan la luz empiezan a morir, empezando por el centro de la retina.",
  },
  {
    icono: "👁️",
    titulo: "Pérdida de visión central",
    detalle:
      "Es la enfermedad de Stargardt tipo 1: se pierde la visión del centro (leer, reconocer caras) mientras la periférica se conserva más tiempo.",
  },
];

export function CausalChain() {
  const [abierto, setAbierto] = useState<number | null>(null);

  return (
    <div className="card">
      <h2>Qué se rompe, paso a paso</h2>
      <p className="muted">Tocá cada paso para ver el detalle.</p>
      <div className="chain">
        {PASOS.map((p, i) => (
          <div key={p.titulo} className="chain-item">
            <button
              className={abierto === i ? "chain-node open" : "chain-node"}
              onClick={() => setAbierto(abierto === i ? null : i)}
            >
              <span className="chain-icon">{p.icono}</span>
              <span className="chain-title">{p.titulo}</span>
            </button>
            {i < PASOS.length - 1 && <span className="chain-arrow">↓</span>}
            {abierto === i && <div className="chain-detail">{p.detalle}</div>}
          </div>
        ))}
      </div>
      <p className="caveat">
        💡 <strong>Por qué un parche y no arreglar el gen:</strong> el manual de
        ABCA4 es muy largo (~6.800 letras) y no entra en el "sobre" que se usa
        normalmente para entregar genes corregidos (capacidad ~4.700). Por eso
        se busca corregir el <em>mensaje</em> en vez de reemplazar el manual.
      </p>
    </div>
  );
}
