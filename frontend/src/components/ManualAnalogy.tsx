/**
 * La analogía central del proyecto, dibujada: el gen como manual con borradores,
 * el splicing como editor que recorta, la mutación como mancha que confunde al
 * editor, y el ASO como cinta que tapa la mancha.
 */
export function ManualAnalogy() {
  return (
    <div className="card">
      <h2>La analogía: un manual con borradores</h2>
      <p className="muted">
        Es la forma más simple de entender qué hace la mutación y qué hace el
        parche.
      </p>

      <svg viewBox="0 0 720 430" className="analogy" role="img">
        {/* ---------- FILA 1: normal ---------- */}
        <text x="8" y="20" className="an-row-label ok">
          ✅ Normal
        </text>
        <g transform="translate(0,32)">
          <rect x="20" y="0" width="110" height="34" rx="4" className="an-exon" />
          <text x="75" y="22" className="an-text">Instrucción</text>

          <rect x="140" y="0" width="200" height="34" rx="4" className="an-intron" />
          <text x="240" y="22" className="an-text dim">notas de borrador</text>

          <rect x="350" y="0" width="110" height="34" rx="4" className="an-exon" />
          <text x="405" y="22" className="an-text">Instrucción</text>

          <text x="490" y="22" className="an-scissors">✂️</text>
          <text x="560" y="17" className="an-note">el editor</text>
          <text x="560" y="30" className="an-note">recorta bien</text>
        </g>
        <g transform="translate(0,86)">
          <rect x="20" y="0" width="220" height="30" rx="4" className="an-result-ok" />
          <text x="130" y="20" className="an-text">Instrucción + Instrucción</text>
          <text x="260" y="20" className="an-note ok">→ pieza funcional 🔧</text>
        </g>

        {/* ---------- FILA 2: con mutación ---------- */}
        <text x="8" y="160" className="an-row-label bad">
          ❌ Con la mutación
        </text>
        <g transform="translate(0,172)">
          <rect x="20" y="0" width="110" height="34" rx="4" className="an-exon" />
          <text x="75" y="22" className="an-text">Instrucción</text>

          <rect x="140" y="0" width="200" height="34" rx="4" className="an-intron" />
          <text x="215" y="22" className="an-text dim">notas</text>
          {/* la mancha */}
          <rect x="248" y="3" width="34" height="28" rx="3" className="an-stain" />
          <text x="265" y="22" className="an-text stain-text">?!</text>
          <text x="265" y="-6" className="an-note bad">mancha</text>

          <rect x="350" y="0" width="110" height="34" rx="4" className="an-exon" />
          <text x="405" y="22" className="an-text">Instrucción</text>

          <text x="490" y="22" className="an-scissors">😵</text>
          <text x="560" y="17" className="an-note bad">el editor</text>
          <text x="560" y="30" className="an-note bad">se confunde</text>
        </g>
        <g transform="translate(0,226)">
          <rect x="20" y="0" width="110" height="30" rx="4" className="an-result-bad" />
          <text x="75" y="20" className="an-text">Instrucción</text>
          <rect x="136" y="0" width="86" height="30" rx="4" className="an-stain" />
          <text x="179" y="20" className="an-text stain-text">basura</text>
          <rect x="228" y="0" width="110" height="30" rx="4" className="an-result-bad" />
          <text x="283" y="20" className="an-text">Instrucción</text>
          <text x="356" y="20" className="an-note bad">→ pieza rota 💀</text>
        </g>

        {/* ---------- FILA 3: con el parche ---------- */}
        <text x="8" y="310" className="an-row-label ok">
          🩹 Con el parche (ASO)
        </text>
        <g transform="translate(0,322)">
          <rect x="20" y="0" width="110" height="34" rx="4" className="an-exon" />
          <text x="75" y="22" className="an-text">Instrucción</text>

          <rect x="140" y="0" width="200" height="34" rx="4" className="an-intron" />
          <text x="200" y="22" className="an-text dim">notas</text>
          <rect x="248" y="3" width="34" height="28" rx="3" className="an-stain" />
          {/* la cinta encima */}
          <rect x="242" y="-2" width="46" height="38" rx="4" className="an-patch" />
          <text x="265" y="22" className="an-text patch-text">🩹</text>
          <text x="265" y="-8" className="an-note ok">cinta</text>

          <rect x="350" y="0" width="110" height="34" rx="4" className="an-exon" />
          <text x="405" y="22" className="an-text">Instrucción</text>

          <text x="490" y="22" className="an-scissors">✂️</text>
          <text x="560" y="17" className="an-note ok">no ve la mancha,</text>
          <text x="560" y="30" className="an-note ok">recorta bien</text>
        </g>
        <g transform="translate(0,376)">
          <rect x="20" y="0" width="220" height="30" rx="4" className="an-result-ok" />
          <text x="130" y="20" className="an-text">Instrucción + Instrucción</text>
          <text x="260" y="20" className="an-note ok">→ pieza funcional 🔧</text>
        </g>
      </svg>

      <p className="muted">
        El parche <strong>no cambia el ADN</strong>: se pega sobre el mensaje ya
        copiado, tapando la señal que confunde. Por eso su efecto es reversible
        y hay que volver a administrarlo.
      </p>
    </div>
  );
}
