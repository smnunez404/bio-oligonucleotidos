# Resultados anteriores a la corrección de CRIT-4

Esta carpeta conserva los resultados generados **antes** de corregir el bug de orientación de hebra
en el cálculo de Tm (CRIT-4 de la revisión adversarial).

## Qué cambió

`pipeline/thermodynamics.py` pasaba la hebra del ASO a `Bio.SeqUtils.MeltingTemp.Tm_NN` con la
tabla `R_DNA_NN1`, cuando Biopython documenta que **debe recibir la hebra de ARN**. La tabla es
asimétrica, así que el orden cambia el número.

## Impacto

| | antes (bug) | después (corregido) |
|---|---|---|
| Embudo del Módulo 4 | 44 candidatos | ver `data/results/` |
| En común | — | 6 |

Estos archivos **no deben usarse para conclusiones nuevas**. Se conservan para poder auditar qué
cambió y verificar que la corrección tuvo el efecto esperado.

Fecha de la corrección: 2026-08-01.
