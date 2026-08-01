/**
 * Explicaciones en lenguaje simple para los términos técnicos que aparecen
 * en la interfaz. Centralizado acá para que la redacción sea consistente
 * entre componentes (varios términos se repiten en distintas vistas).
 */
export const glossary = {
  gene: "Un gen es como una 'receta' dentro del ADN que le dice al cuerpo cómo fabricar una proteína específica. ABCA4 es el gen (la receta) que fabrica la proteína ABCA4, encargada de 'limpiar' una sustancia tóxica en la retina.",

  variantNotation:
    "Esta es la forma estándar de nombrar una mutación puntual: indica en qué posición exacta del gen está el cambio, y qué letra (base) cambió por cuál otra. No hace falta memorizar el formato, solo saber que identifica una mutación específica y única.",

  transcript:
    "Es el 'ID de versión oficial' del gen que usan los científicos como referencia común — como la edición estándar de un libro, para que todos hablen exactamente de la misma secuencia.",

  intron:
    "Los genes tienen partes que se usan para fabricar la proteína (exones) y partes que se recortan y descartan antes de eso (intrones). Esta mutación está en una parte que normalmente se recorta (intrón 2) — el problema es que cambia una señal que le dice al cuerpo CÓMO recortarla, y ahí es donde falla.",

  genomicCoordinate:
    "Es la 'dirección exacta' de la mutación en el genoma humano completo — como la calle y el número de una casa, pero para ADN. GRCh38 es la versión del 'mapa' del genoma humano usada como referencia estándar hoy.",

  wildtype:
    "Wild-type significa 'la versión normal/sana': cómo se ve la secuencia en una persona sin esta mutación.",

  mutant:
    "Es la misma secuencia, pero con el error genético ya puesto — así se ve en una persona con la enfermedad.",

  variantBase:
    "Esta es la única letra que cambia entre las dos versiones. Un solo cambio (G por A) es la causa de todo el problema — por eso a veces se le dice mutación 'puntual'.",

  cryoEM:
    "Crio-microscopía electrónica: una técnica de laboratorio que congela las moléculas y las 'fotografía' con un microscopio de electrones para ver su forma real en 3D. No es una predicción de computadora — es una medición real hecha en laboratorio.",

  pdb:
    "Protein Data Bank (PDB): una base de datos mundial y pública donde los científicos publican las estructuras 3D de proteínas que lograron medir en laboratorio.",

  resolution:
    "La resolución dice qué tan 'nítida' es la medición (se mide en Ångström, Å). Cuanto más bajo el número, más nítido el detalle — es como la diferencia entre una foto borrosa y una foto en alta definición.",

  nRetPE:
    "N-ret-PE es una sustancia que el ojo produce naturalmente al captar luz. La proteína ABCA4 normalmente la 'saca' de la célula. Si ABCA4 no funciona, esta sustancia se acumula y se vuelve tóxica para la retina — así es como esta mutación termina causando pérdida de visión.",

  aso:
    "ASO (oligonucleótido antisentido): un fragmento corto de material genético sintético, diseñado a medida para pegarse a una parte específica del ARN y bloquear una señal que está fallando — funciona como un 'parche' molecular.",

  splicing:
    "Splicing (empalme): el proceso por el cual la célula recorta las partes no usadas del ARN (intrones) y pega entre sí las partes que sí se usan (exones), antes de fabricar la proteína.",

  pseudoexon:
    "Un pseudoexón es un pedazo de intrón (que normalmente se recorta y descarta) que, por culpa de la mutación, la célula confunde con un exón y lo deja pegado por error — como si el corrector ortográfico 'corrigiera' algo que estaba bien.",

  oligoWalk:
    "Oligo-Walk ('caminata de oligos'): en vez de adivinar un solo diseño de parche molecular, se generan TODAS las combinaciones posibles, una por cada posición, desplazando una 'ventana' de a un nucleótido por vez a lo largo de la región. Así no se descarta ningún candidato por no haberlo probado.",

  slidingWindow:
    "Una 'ventana deslizante' recorta un pedazo de tamaño fijo (por ejemplo 20 letras) de la secuencia, y lo va desplazando de a una posición: primero letras 1-20, después 2-21, después 3-22... Cada posición genera un candidato distinto.",

  antisenseSequence:
    "Esta es la secuencia real del parche (el ASO), no la del ARN. Se construye 'al revés y complementaria' de la ventana del ARN, porque así es como se puede pegar a ella por apareamiento de bases — como un molde y su contramolde.",

  coversVariant:
    "Indica si ese candidato específico 'tapa' físicamente la posición exacta de la mutación. Es un primer indicio de relevancia — pero no alcanza solo con esto: los módulos que siguen (filtros, termodinámica, etc.) van a decidir cuáles son realmente buenos candidatos.",

  intronBounds:
    "El intrón 2 real mide 1393 nt (confirmado con datos reales de Ensembl, no supuesto). Un buen parche molecular tiene que quedar completamente adentro del intrón — si una ventana se extendiera hacia el exón vecino, taparía una parte del ARN que SÍ se necesita, lo cual sería contraproducente. Por eso el sistema recorta automáticamente la búsqueda para no cruzar ese límite.",

  gcContent:
    "El porcentaje de GC mide cuántas letras del parche son G o C (en vez de A o T). Importa porque G y C se pegan más fuerte entre sí que A y T (3 puentes de hidrógeno vs. 2). Muy poco GC = el parche no se pega con suficiente fuerza. Demasiado GC = se pega TAN fuerte que puede formar nudos con sigo mismo en vez de pegarse donde debería. Por eso se busca un rango intermedio (40%-70%).",

  gRun:
    "Un 'G-run' es una racha de 4 o más letras G seguidas. Estas rachas tienden a doblarse sobre sí mismas formando una estructura llamada G-cuádruplex, que 'atasca' al parche en una forma inútil — como si el parche se hiciera un nudo antes de llegar a destino. Por eso se descartan.",

  donorSite:
    "Un 'sitio donador' es la señal que le dice a la célula dónde EMPIEZA un intrón (o sea, dónde cortar). Tiene una forma reconocible: casi siempre empieza con las letras GT. Cuanto más se parece la secuencia a la 'forma ideal' que la célula espera, más fuerte es la señal y más probable que la célula la use.",

  consensusMatch:
    "El 'consenso' es la forma ideal que suele tener un sitio donador. Contamos en cuántas de las 9 posiciones la secuencia real coincide con esa forma ideal: más coincidencias = señal más fuerte. Ojo: esto es una regla simple de comparación, NO un predictor entrenado — el análisis serio con inteligencia artificial (SpliceAI) viene en un módulo posterior.",

  crypticSite:
    "Un sitio 'críptico' es una señal de corte que está latente en el ADN pero que la célula normalmente ignora porque es demasiado débil. Si una mutación la fortalece lo suficiente, la célula empieza a usarla por error — y ahí es donde aparece el pseudoexón.",

  mfe:
    "MFE = energía libre mínima. Es la forma plegada más estable que adopta el ARN, la que 'prefiere' adoptar. Cuanto más negativo el número, más fuertemente plegado está. Un ARN muy plegado tiene más zonas escondidas e inalcanzables.",

  meltingTemp:
    "La temperatura de fusión (Tm) es la temperatura a la que el parche se despega de su objetivo. Si es muy baja, el parche no aguanta pegado a temperatura del cuerpo (37 °C). Si es muy alta, se pega demasiado fuerte y puede quedarse pegado también donde no debe.",

  freeEnergy:
    "La energía libre (ΔG) mide qué tan estable es una unión, en kcal/mol. Cuanto MÁS NEGATIVO, más estable y más difícil de deshacer. Acá se usa para tres cosas distintas: cuánto se pega el parche a su objetivo (queremos muy negativo), cuánto se dobla sobre sí mismo (NO queremos muy negativo) y cuánto se pega a otra copia de sí mismo (tampoco queremos).",

  hairpin:
    "Una 'horquilla' pasa cuando el parche se dobla sobre sí mismo y se pega a su propia cola, como un cordón que se hace un nudo. Si eso ocurre, el parche está ocupado consigo mismo y no puede pegarse al ARN que queremos tapar.",

  homodimer:
    "Un 'homodímero' es cuando dos copias del mismo parche se pegan entre sí en vez de pegarse al objetivo. Es el mismo problema que la horquilla pero de a dos: el parche se neutraliza solo.",

  accessibility:
    "El ARN no es una cinta recta: se pliega sobre sí mismo. Si la zona que queremos tapar está escondida dentro de un pliegue, el parche no puede llegar aunque encaje perfecto. Esto mide qué tan expuesta está esa zona. Como el valor absoluto es diminuto y difícil de interpretar, mostramos el PERCENTIL: 100 = la zona más expuesta de todos los candidatos.",

  percentile:
    "Un percentil compara este candidato contra todos los demás del lote, en vez de dar un número absoluto. Percentil 90 = mejor que el 90% de los candidatos en esa métrica. Es más confiable que el valor absoluto cuando el método de cálculo tiene incertidumbre.",

  offTarget:
    "Off-target (fuera de blanco): el riesgo de que el parche molecular se pegue, por error, a un ARN de OTRO gen que se parezca lo suficiente al que buscamos. Si eso pasa, el parche podría bloquear algo que la célula sí necesita, en un lugar del cuerpo donde no debería actuar.",

  transcriptome:
    "El transcriptoma es el conjunto de TODOS los ARN que una célula puede fabricar a partir del genoma completo. Compararlo contra el transcriptoma es más rápido que contra el genoma entero, pero tiene un límite: no cubre partes del ADN que no se transcriben a ARN (donde, en teoría, un parche no tendría nada a lo que pegarse).",

  blast:
    "BLAST es el programa estándar en bioinformática para buscar, entre millones de secuencias, cuáles se parecen a la nuestra. Es la misma idea que un buscador de texto ('¿dónde aparece esto o algo parecido?'), pero adaptado a letras de ADN/ARN en vez de palabras.",

  offTargetRule:
    "La regla técnica: un hit de BLAST cuenta como off-target si encuentra, en OTRO gen, un tramo de 15 letras o más que coincide con 4 o menos diferencias. Antes esto descartaba al candidato automáticamente; ahora solo clasifica su SEVERIDAD (ver más abajo) -- ningún candidato se elimina por esto todavía.",

  offTargetSeverity:
    "Nivel de riesgo del candidato, no un veredicto. Se mide por el TRAMO SEGUIDO de letras que coinciden sin ninguna interrupción con otro gen -- como buscar la frase repetida más larga entre dos textos: importa el tramo intacto, no cuántas palabras distintas hay en total. \"alto\" = 18 o más letras seguidas; \"moderado\" = 16-17; \"leve\" = 13-15; \"sin señal\" = 12 o menos. Se mide el tramo seguido y no la cantidad de diferencias porque lo que hace que dos hebras se peguen fuerte es la corrida sin cortes: una diferencia justo en el medio parte la unión en dos pedazos débiles, mientras que la misma diferencia en la punta casi no molesta. Los ASOs como el nuestro (PMO) no cortan el ARN, solo lo bloquean físicamente -- por eso una coincidencia en otro gen solo es grave si cae justo en una zona que ese gen usa activamente, algo que este módulo todavía no puede saber. Por eso es una señal para revisar, no un filtro automático.",

  asoMasking:
    "Cómo simulamos que el parche tapa el ARN: reemplazamos su ventana por la letra N, que el predictor codifica como \"acá no hay información legible\". Es la analogía de poner cinta opaca sobre un renglón y preguntarle al lector qué entiende ahora. Sirve porque un PMO no corta el ARN ni lo modifica: se pega encima y lo tapa. Límite importante: el enmascarado es todo-o-nada, asume que el parche cubre el 100% de las moléculas y que bloquea perfectamente, cosa que ningún oligo real hace.",

  crypticPair:
    "Los sitios de splicing funcionan de a pares: un \"aceptor\" (donde empieza el trozo que se pega) solo sirve si hay un \"donador\" (donde termina) con el que emparejarse. Por eso tapar una sola de las dos puntas puede desarmar el pseudoexón entero — es como quitar un solo extremo de una cremallera: el resto ya no cierra.",

  counterproductive:
    "Un candidato contraproducente es uno que, al taparlo, SUBE la probabilidad del sitio falso en vez de bajarla. Suena raro, pero el predictor mira el contexto: si la ventana que tapamos contenía señales que competían con el sitio falso o lo debilitaban, borrarlas lo deja más despejado. Estos candidatos pasaban los filtros anteriores como cualquier otro, porque esos filtros miran propiedades físicas del oligo y no la dirección del efecto.",

  passedFilter:
    "Indica si este candidato sobrevivió el filtro rápido (GC% + sin G-runs). Pasar este filtro NO significa que sea un buen ASO todavía — solo que no tiene un problema obvio y merece pasar a los análisis más caros (termodinámica, off-target, splicing) en los próximos módulos.",
} as const;
