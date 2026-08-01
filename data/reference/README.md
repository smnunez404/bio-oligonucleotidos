# Datos de referencia — Módulo 5 (off-target)

Esta carpeta contiene la base de datos BLAST del transcriptoma humano usada
por `pipeline/off_target.py`. **No se versiona en git** (ver `.gitignore`):
son ~400 MB de archivos binarios/derivados que se pueden regenerar
íntegramente desde Ensembl en unos minutos. Ver también la decisión de
arquitectura documentada en la wiki:
`wiki/decisiones/0005-usar-blast-local-contra-transcriptoma-cdna-ncrna.md`.

## Archivos que debería haber acá

- `Homo_sapiens.GRCh38.cdna.all.fa.gz` — transcritos codificantes (Ensembl release 114)
- `Homo_sapiens.GRCh38.ncrna.fa.gz` — transcritos no codificantes (Ensembl release 114)
- `human_transcriptome_db.*` — índice BLAST (`makeblastdb -dbtype nucl`) combinando ambos FASTA
- `transcript_gene_map.tsv` — mapeo `transcript_id -> gene_id -> gene_symbol`, parseado de los headers FASTA

## Cómo regenerarlos

Requiere el entorno conda `bio-oligo` (BLAST+ + Biopython) o equivalente
con `blastn`/`makeblastdb` en el PATH.

```bash
cd data/reference

# 1. Descargar cDNA (codificante) y ncRNA (no codificante) de Ensembl GRCh38
curl -O https://ftp.ensembl.org/pub/release-114/fasta/homo_sapiens/cdna/Homo_sapiens.GRCh38.cdna.all.fa.gz
curl -O https://ftp.ensembl.org/pub/release-114/fasta/homo_sapiens/ncrna/Homo_sapiens.GRCh38.ncrna.fa.gz

# 2. Descomprimir y combinar en un único FASTA para indexar
gunzip -k Homo_sapiens.GRCh38.cdna.all.fa.gz
gunzip -k Homo_sapiens.GRCh38.ncrna.fa.gz
cat Homo_sapiens.GRCh38.cdna.all.fa Homo_sapiens.GRCh38.ncrna.fa > human_transcriptome.fa

# 3. Construir el índice BLAST
makeblastdb -in human_transcriptome.fa -dbtype nucl \
    -out human_transcriptome_db \
    -title "Homo_sapiens GRCh38 cdna+ncrna Ensembl114"

# 4. Limpiar intermedios (los .gz ya alcanzan para reproducir; el .fa sin
#    comprimir y el combinado no hacen falta después de indexar)
rm -f Homo_sapiens.GRCh38.cdna.all.fa Homo_sapiens.GRCh38.ncrna.fa human_transcriptome.fa
```

El mapeo transcrito→gen se genera parseando los headers FASTA (formato
Ensembl: `>ENST... gene:ENSG... gene_symbol:SYMBOL ...`) — ver la función
`load_gene_map` en `pipeline/off_target.py` para el formato TSV esperado
(`transcript_id\tgene_id\tgene_symbol`), y el ADR 0005 en la wiki para el
snippet de generación completo.

## Verificación de integridad

```bash
blastdbcmd -db human_transcriptome_db -info
# Esperado: 410,920 sequences; 596,956,857 total bases (Ensembl release 114)
```

## Nota de reproducibilidad

Este README documenta el estado tal como se construyó el 2026-07-29. Si en
el futuro se usa un release distinto de Ensembl, los conteos de secuencias
y bases de arriba van a diferir — no es un error, hay que actualizar esta
nota con el nuevo release y los nuevos conteos para que quede trazable.
