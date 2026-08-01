import { useEffect, useRef, useState } from "react";
import * as $3Dmol from "3dmol";
import { InfoTip } from "./InfoTip";
import { glossary } from "../glossary";

const PDB_ID = "7M1Q";
const PDB_URL = `https://files.rcsb.org/download/${PDB_ID}.pdb`;

/**
 * Muestra la estructura experimental (crio-EM) real de ABCA4 humana, no una
 * predicción de AlphaFold: ya existe una estructura resuelta, así que no hace
 * falta (ni conviene) volver a predecirla. Ver wiki/decisiones/0004 en el
 * vault del proyecto para la justificación completa.
 *
 * Esto es explicativo (contexto de por qué la variante es dañina), no forma
 * parte del scoring de candidatos ASO — eso ocurre a nivel de ácido nucleico.
 */
export function ProteinViewer() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading"
  );
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!containerRef.current) return;
      try {
        const res = await fetch(PDB_URL);
        if (!res.ok) throw new Error(`RCSB respondió ${res.status}`);
        const pdbText = await res.text();
        if (cancelled) return;

        const viewer = $3Dmol.createViewer(containerRef.current, {
          backgroundColor: "0xffffff00" as unknown as string, // transparente
        });
        viewer.addModel(pdbText, "pdb");
        viewer.setStyle({}, { cartoon: { color: "spectrum" } });
        // N-ret-PE (el sustrato transportado) como heteroátomo, resaltado aparte.
        viewer.setStyle(
          { hetflag: true },
          { stick: { colorscheme: "orangeCarbon" } }
        );
        viewer.zoomTo();
        viewer.render();
        setStatus("ready");
      } catch (err) {
        if (!cancelled) {
          setErrorMsg(err instanceof Error ? err.message : String(err));
          setStatus("error");
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="card">
      <h2>
        Proteína ABCA4 — estructura experimental (
        <InfoTip text={glossary.pdb}>PDB</InfoTip> {PDB_ID})
      </h2>
      <p className="muted">
        <InfoTip text={glossary.cryoEM}>Crio-EM</InfoTip>,{" "}
        <InfoTip text={glossary.resolution}>2.92 Å</InfoTip>, humana, en
        complejo con <InfoTip text={glossary.nRetPE}>N-ret-PE</InfoTip> — el
        sustrato que ABCA4 transloca y que se acumula (formando compuestos
        tóxicos) cuando la proteína pierde función. Es la estructura real ya
        resuelta en laboratorio, no una predicción: no hace falta AlphaFold
        para esto.
      </p>
      {status === "loading" && (
        <p className="muted">Cargando estructura desde RCSB…</p>
      )}
      {status === "error" && (
        <p className="muted">No se pudo cargar la estructura: {errorMsg}</p>
      )}
      <div
        ref={containerRef}
        style={{
          width: "100%",
          height: "420px",
          position: "relative",
          borderRadius: "8px",
          overflow: "hidden",
          background: "var(--bg)",
        }}
      />
      <p className="muted" style={{ marginTop: "8px" }}>
        Fuente: RCSB PDB{" "}
        <a
          href={`https://www.rcsb.org/structure/${PDB_ID}`}
          target="_blank"
          rel="noreferrer"
        >
          {PDB_ID}
        </a>
        . Esta vista es contextual/explicativa — no participa del scoring de
        candidatos ASO, que ocurre enteramente a nivel de ARN.
      </p>
    </div>
  );
}
