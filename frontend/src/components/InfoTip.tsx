import { useEffect, useRef, useState } from "react";

interface Props {
  text: string;
  /** Texto visible junto al ícono (opcional). Si no se pasa, solo se ve el ícono ⓘ. */
  children?: React.ReactNode;
}

/**
 * Ícono "ⓘ" inline: al tocarlo, muestra una explicación breve en lenguaje
 * simple. Pensado para no saturar la pantalla — la explicación solo aparece
 * si el usuario la pide.
 */
export function InfoTip({ text, children }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [open]);

  return (
    <span className="infotip" ref={ref}>
      {children}
      <button
        type="button"
        className="infotip-icon"
        aria-label="¿Qué significa esto?"
        onClick={() => setOpen((v) => !v)}
      >
        ⓘ
      </button>
      {open && (
        <span className="infotip-bubble" role="tooltip">
          {text}
        </span>
      )}
    </span>
  );
}
