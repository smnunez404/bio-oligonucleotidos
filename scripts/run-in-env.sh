#!/usr/bin/env bash
# Corre un comando dentro del entorno `bio-oligo`, lo encuentre donde lo encuentre.
#
# POR QUÉ EXISTE
# --------------
# `.claude/launch.json` invocaba `python` a secas. En una máquina donde el
# entorno no está activado eso falla de dos formas distintas, y ninguna es
# obvia:
#
#   1. `python` puede no existir (en Ubuntu suele haber solo `python3`).
#   2. Puede existir pero sin las dependencias, y entonces el error aparece
#      recién al importar fastapi o ViennaRNA.
#
# Peor todavía: aunque el `python` sea el correcto, el Módulo 5 necesita
# `blastn` en el PATH (`pipeline/off_target.py` lo busca con `shutil.which`).
# Un intérprete correcto sin el PATH del entorno hace que `/api/off-target`
# devuelva 503 aunque BLAST esté instalado — que es exactamente el error de
# diagnóstico que quedó documentado en la bitácora del 2026-07-31.
#
# USO
# ---
#   scripts/run-in-env.sh python -m uvicorn backend.main:app --port 8000
#   scripts/run-in-env.sh python -m pytest tests/
#   scripts/run-in-env.sh blastn -version
#
# Se puede forzar un entorno concreto con BIO_OLIGO_ENV=/ruta/al/env.

set -euo pipefail

ENV_NAME="${BIO_OLIGO_ENV_NAME:-bio-oligo}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ $# -eq 0 ]; then
  echo "uso: $(basename "$0") <comando> [args...]" >&2
  exit 2
fi

# Pangolin lo necesita siempre, y ponerlo acá no molesta a los demás.
export KMP_AFFINITY="${KMP_AFFINITY:-disabled}"
# Para que `import pipeline...` funcione sin instalar el paquete.
export PYTHONPATH="${PYTHONPATH:-$REPO_ROOT}"

# 1) Ruta explícita, si el usuario la dio.
if [ -n "${BIO_OLIGO_ENV:-}" ]; then
  export PATH="$BIO_OLIGO_ENV/bin:$PATH"
  exec "$@"
fi

# 2) conda, si está en el PATH.
if command -v conda >/dev/null 2>&1; then
  exec conda run --no-capture-output -n "$ENV_NAME" "$@"
fi

# 3) micromamba (así gestiona Claude Science sus entornos).
for mm in \
  "${MAMBA_EXE:-}" \
  "$HOME/.claude-science/conda/bin/micromamba" \
  "$(command -v micromamba 2>/dev/null || true)"
do
  if [ -n "$mm" ] && [ -x "$mm" ]; then
    root="${MAMBA_ROOT_PREFIX:-$HOME/.claude-science/conda}"
    if [ -d "$root/envs/$ENV_NAME" ]; then
      export MAMBA_ROOT_PREFIX="$root"
      exec "$mm" run -n "$ENV_NAME" "$@"
    fi
  fi
done

# 4) El env sin driver: su `bin/` alcanza para correr, solo hay que anteponerlo.
for candidate in \
  "$HOME/.claude-science/conda/envs/$ENV_NAME" \
  "$HOME/miniconda3/envs/$ENV_NAME" \
  "$HOME/anaconda3/envs/$ENV_NAME" \
  "$HOME/micromamba/envs/$ENV_NAME"
do
  if [ -x "$candidate/bin/python" ]; then
    export PATH="$candidate/bin:$PATH"
    exec "$@"
  fi
done

cat >&2 <<EOF
ABORTA: no se encontró el entorno '$ENV_NAME'.

Se buscó, en orden: BIO_OLIGO_ENV, conda, micromamba y las rutas habituales de
envs. Crealo como documenta el README:

    conda create -n $ENV_NAME python=3.11
    conda install -n $ENV_NAME -c conda-forge -c bioconda viennarna blast
    conda run -n $ENV_NAME pip install -r requirements/bio-oligo.txt

O apuntá a uno existente:

    BIO_OLIGO_ENV=/ruta/al/env $0 $*
EOF
exit 1
