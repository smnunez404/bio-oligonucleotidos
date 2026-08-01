# Tarea: agregar la pestaña "Bloqueo del ASO" (Módulo 6b) a la plataforma visual

Repo: `bio-oligonucleotidos`. El backend ya está hecho y andando — **no lo toques**.
Tu trabajo es solo el frontend (React + TypeScript + Vite).

## Contexto de dominio (para que los textos de la UI sean correctos)

El proyecto diseña un "parche molecular" (oligonucleótido antisentido, química PMO)
para corregir un error de splicing causado por la variante ABCA4 c.161-395G>A
(enfermedad de Stargardt). La variante crea dos sitios de splicing falsos
("crípticos") que hacen que la célula inserte un trozo de basura ("pseudoexón") en
el mensaje del gen:

- **donador críptico** en +1 respecto de la variante
- **aceptor críptico** en −89 respecto de la variante
- entre los dos definen un pseudoexón de **91 pb**, que coincide exactamente con
  uno medido en laboratorio (PE1b) por Peng et al. 2025 — validación cruzada.

El Módulo 6b simula qué pasa si un ASO **tapa** una región: se reemplaza esa
ventana por `N`, que SpliceAI codifica como vector nulo ("acá no hay información
legible"). Es un proxy del bloqueo estérico de un PMO, que no corta el ARN — lo tapa.

**El mensaje central de la pestaña**, y lo que el usuario tiene que entender al
mirarla: de los 44 candidatos finales, solo 3 sirven, 10 son activamente
contraproducentes, y ninguno cubre la segunda diana.

## El endpoint (ya funciona)

`GET /api/aso-masking` y `GET /api/aso-masking?classification=bloquea|contraproducente|sin_efecto`

Levantá el backend con `uvicorn backend.main:app --reload` y mirá la respuesta real
en `http://localhost:8000/docs` antes de escribir tipos. Forma de la respuesta:

```
{
  "method": string,          // cómo se simula el bloqueo
  "limitation": string,      // MOSTRAR SIEMPRE en la UI, ver abajo
  "predictor": string,       // dice explícitamente que NO es un ensemble
  "baseline": { "donor_cryptic": 0.5595, "acceptor_cryptic": 0.2709, "donor_canonical_e3": 0.9893 },
  "controls": [ { "name", "label", "donor_cryptic", "delta_donor", "expected", "ok" } ],  // 4
  "thresholds": { "block": -0.43, "counterproductive": 0.1 },
  "sites": { "donor_cryptic_offset": 1, "acceptor_cryptic_offset": -89,
             "pseudoexon_size": 91, "pseudoexon_note": string },
  "total": 44,
  "counts": { "bloquea": 3, "sin_efecto": 31, "contraproducente": 10 },
  "candidates_covering_acceptor": 0,
  "acceptor_gap_note": string,
  "candidates": [ {
      "name": "cand_5992", "start_rel": -8, "end_rel": 12, "covers_donor": true,
      "donor_cryptic": 0.0, "delta_donor": -0.5595,
      "acceptor_cryptic": 0.0533, "delta_acceptor": -0.2176,
      "donor_canonical_e3": 0.9915, "delta_canonical": 0.0022,
      "classification": "bloquea"
  } ]
}
```

## Qué construir

### 1. Pestaña nueva en `frontend/src/App.tsx`
- Agregá `"asomasking"` al tipo de `tab` y un botón **"Bloqueo del ASO"** en `<nav className="tabs">`, después de "Off-target" (es el último).
- Registrala en `MODULE_OF_TAB` como módulo **6**.
- Usá el `<ModuleIntro>` existente, con el mismo tono didáctico que las otras pestañas
  (el usuario es de software, no de biología — analogías, no jerga):
  - `title`: `"Módulo 6b — ¿el parche realmente apaga el sitio falso?"`
  - `goal`: explicá que hasta acá teníamos 44 candidatos que cumplen requisitos
    fisicoquímicos, pero **nadie había verificado si sirven para lo que se diseñaron**.
  - `detail`: la analogía del bloqueo. Un PMO no corta nada: se pega y tapa, como
    poner cinta opaca sobre un renglón. Para simularlo le decimos al predictor "esta
    región no se puede leer" y medimos si el sitio falso se apaga.

### 2. Componente `frontend/src/components/AsoMaskingScatter.tsx`
Gráfico de dispersión, el corazón de la pestaña. Mirá `OligoWalkTrack.tsx` para el
estilo de SVG que ya usa el proyecto y respetalo.
- Eje X: `start_rel + 10` (centro del ASO), rango −190 a 180.
- Eje Y: `delta_donor`, rango −0,64 a 0,29.
- Banda verde de −0,64 a `thresholds.block` (−0,43) = "bloqueo efectivo".
- Banda naranja de `thresholds.counterproductive` (0,10) a 0,29 = "contraproducente".
- Línea vertical roja punteada en x=1 (donador críptico), azul punteada en x=−89 (aceptor críptico), rotuladas.
- Puntos: rojo si `classification==="bloquea"`, naranja si `"contraproducente"`, gris si `"sin_efecto"`.
- **Tooltip al hover** con: nombre, ventana (`start_rel..end_rel`), delta del donador,
  score resultante del donador, y delta del aceptor.
- Clic en un punto → selecciona esa fila en la tabla (scroll + highlight).

### 3. Componente `frontend/src/components/AsoMaskingTable.tsx`
Seguí el patrón de `OffTargetTable.tsx` (que ya tiene filtro por severidad — acá es
lo mismo pero por clasificación).
- Columnas: candidato, ventana (rel. a la variante), clasificación (chip de color),
  donador +1 (score y delta), aceptor −89 (score y delta), donador canónico E3 (delta).
- Filtro por clasificación con los conteos al lado: `bloquea (3)`, `sin_efecto (31)`,
  `contraproducente (10)`. Usá el filtro del backend (`?classification=`) o filtrá en
  cliente, como prefieras — pero los conteos vienen de `counts`.
- Orden por defecto: `delta_donor` ascendente (los que bloquean, primero).
- La columna del donador canónico debe dejar claro que **ninguno lo toca** (todos
  |delta| < 0,05): es la evidencia de que los ASO no dañan el splicing sano.

### 4. Componente `frontend/src/components/AsoMaskingControls.tsx`
Los 4 controles, en una tabla chica. **Esto no es decorativo**: sin controles el
resultado no es interpretable, y la pestaña tiene que mostrar que se hicieron.
Columnas: control, qué verifica (`expected`), delta medido, ✓/✗ (`ok`).
Poné un título tipo "Cómo sabemos que el método mide algo real" y una línea que
explique el control clave: enmascarar el donador canónico del exón 3 anula **ese**
sitio y no el críptico, lo que prueba que el efecto es local y no un artefacto.

### 5. Tres callouts con los hallazgos
Usá `<TensionCallout>` si encaja, o `<ModuleIntro>`/divs con las clases CSS existentes.
Ordenados así:

1. **Verde — "Tapar una punta desarma el pseudoexón entero".** Los 3 candidatos que
   cubren el donador lo llevan a 0,000 **y además** hunden el aceptor de −89 (0,27 →
   0,04) **sin cubrirlo**. Eso significa que el predictor entendió que los dos sitios
   funcionan de a pares: un aceptor solo sirve si hay un donador con el que
   emparejarse. Conclusión práctica: no hace falta tapar las dos puntas.
2. **Naranja — "10 de 44 candidatos empeorarían el problema".** Suben el score del
   donador en vez de bajarlo; el peor lo lleva de 0,5595 a 0,7694 (+0,21). El pipeline
   hasta ahora no los distinguía: salían del embudo como equivalentes a los demás.
3. **Rojo — "Una de las dos dianas quedó sin candidatos".** Ninguno de los 44 cubre el
   aceptor de −89. Del barrido inicial, 20 lo cubrían: 16 murieron en los filtros
   heurísticos (GC, corridas de G) y los 4 restantes en termodinámica (3 por homodímero
   demasiado estable, 1 por Tm baja). Los filtros funcionaron bien; el problema es que
   esa región es hostil para un oligo de 20 nt con los parámetros actuales. Usá
   `acceptor_gap_note` del endpoint.

### 6. Actualizar `frontend/src/components/PipelineFunnel.tsx`
El embudo hoy muestra 381 → 276 → 44. Agregá la etapa del Módulo 6b: de los 44,
**3 bloquean / 31 sin efecto / 10 contraproducentes**. Ojo: **no es un filtro más** —
el módulo no descarta candidatos, los clasifica (igual que off-target anota severidad
sin descartar). Que el diseño visual refleje esa diferencia y no parezca otro
estrechamiento del embudo.

## Regla no negociable del proyecto

Toda afirmación en la UI tiene que declarar su límite. Este módulo **no mide eficacia**:
el enmascarado es binario y total (asume que el ASO ocupa el 100 % de las moléculas y
bloquea perfectamente), mientras un ASO real tiene afinidad finita y compite con
proteínas de unión a ARN. Es una condición **necesaria pero no suficiente**.

Mostrá el texto de `limitation` de forma visible y permanente (no en un tooltip que
haya que descubrir). Usá el componente `<InfoTip>` para los términos técnicos.
Y donde nombres el predictor, usá el campo `predictor`: dice explícitamente que corre
**un solo predictor y NO es un ensemble** — Pangolin está diferido y no debe
describirse como si ya estuviera.

## Verificación antes de terminar

1. `npm run build` sin errores de TypeScript.
2. Levantá backend + frontend y **abrí la pestaña en el navegador**. Comprobá:
   los 3 puntos rojos caen sobre la línea del donador (x≈1) y en la banda verde;
   los 10 naranjas están en la banda naranja; el tooltip funciona; el filtro cambia
   la tabla y los conteos dan 3/31/10.
3. Que los textos de límites se lean sin interactuar con nada.
4. Revisá que no haya solapamiento de etiquetas en el SVG a ancho de ventana chico.

Contame qué decisiones de diseño visual tomaste y si algún dato del endpoint te
resultó ambiguo o difícil de representar.
