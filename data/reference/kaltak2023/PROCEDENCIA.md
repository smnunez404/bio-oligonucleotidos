# Procedencia de `aon_sequences.csv`

Las 32 secuencias de oligonucleótido antisentido de este archivo fueron extraídas de la
**Tabla S1** del material suplementario de:

> Kaltak M, de Bruijn P, Piccolo D, Lee S-E, Dulla K, Hoogenboezem T, Beumer W, Webster AR,
> Collin RWJ, Cheetham ME, Platenburg G, Swildens J.
> *Antisense oligonucleotide therapy corrects splicing in the common Stargardt disease type
> 1-causing variant.*
> **Mol Ther Nucleic Acids** (2023). DOI: 10.1016/j.omtn.2023.02.020 · PMID 36910710 · PMC9999166.

## Qué se versiona y qué no

- ✅ **`aon_sequences.csv`** — sí. Son secuencias biológicas publicadas (hechos científicos), y sin
  ellas la calibración del pipeline no es reproducible.
- ❌ **El PDF y el XLSX del suplemento** — no. Son documentos con copyright de Elsevier. Están
  excluidos por `.gitignore`.

## Cómo obtener el suplemento completo

PMC devuelve un reCAPTCHA en la ruta `/bin/`. La vía que funciona:

```bash
# 1. Obtener el PII real del artículo
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=9999166&retmode=xml" \
  | grep -oE '<article-id pub-id-type="pii">[^<]+'
#    -> S2162-2531(23)00040-9  ->  S2162253123000409

# 2. Descargar del CDN de Elsevier
curl -L -o mmc1.pdf \
  "https://ars.els-cdn.com/content/image/1-s2.0-S2162253123000409-mmc1.pdf"
```

El artículo es de acceso abierto (CC BY-NC-ND).
