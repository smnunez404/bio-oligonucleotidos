"""Lint del vault de Obsidian — implementa la operación "Lint" de AGENTS.md.

QUÉ REVISA
----------
1. Wikilinks rotos: `[[destino]]` que no resuelve a ningún archivo del vault.
2. Páginas huérfanas: páginas de `wiki/` a las que no apunta nadie.
3. Fuentes sin ficha: archivos en `raw/` sin su página en `wiki/fuentes/`.

LA TRAMPA QUE MOTIVÓ ESCRIBIRLO BIEN
-------------------------------------
Un chequeo ingenuo con `re.findall(r"\\[\\[(...)\\]\\]")` marca como roto el
ejemplo de la propia convención en AGENTS.md:

    - Wikilinks con ruta desde la raíz: `[[wiki/conceptos/ejemplo]]`.

Ese texto está dentro de backticks, y **Obsidian no interpreta wikilinks dentro
de un code span ni de un bloque de código**: los muestra literales. O sea que no
es un enlace roto — el falso positivo estaba en el verificador, no en el vault.

Por eso este script elimina primero los bloques ``` y los code spans `...` antes
de buscar enlaces. Es la diferencia entre un lint en el que se puede confiar y
uno que enseña a ignorar sus propias alertas.

USO
---
    python scripts/lint_vault.py [ruta-al-vault]

Sale con código 1 si encuentra enlaces rotos (lo único que se considera error);
lo demás se reporta como aviso.
"""

from __future__ import annotations

import os
import re
import sys

DEFAULT_VAULT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "bio-oligonucleotidos-obsidian",
)

SKIP_DIRS = {".obsidian", ".git", ".trash", "_templates"}
ASSET_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".pdf", ".csv", ".json")

# Bloques ``` primero, después los code spans de uno o más backticks.
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
SPAN_RE = re.compile(r"(`+)[^`]*?\1")
LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def strip_code(text: str) -> str:
    """Saca bloques y spans de código, donde los `[[...]]` son literales."""
    return SPAN_RE.sub(" ", FENCE_RE.sub(" ", text))


def wikilinks(text: str) -> list[str]:
    """Destinos de los wikilinks reales, sin alias (`|`) ni anclas (`#`)."""
    out = []
    for raw in LINK_RE.findall(strip_code(text)):
        target = raw.split("|")[0].split("#")[0].strip()
        if target:
            out.append(target)
    return out


def collect(vault: str) -> dict[str, str]:
    """{ruta relativa -> ruta absoluta} de todo lo enlazable."""
    found = {}
    for root, dirs, names in os.walk(vault):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for n in names:
            if n.endswith(".md") or n.lower().endswith(ASSET_EXT):
                full = os.path.join(root, n)
                found[os.path.relpath(full, vault).replace(os.sep, "/")] = full
    return found


def resolve(target: str, files: dict[str, str]) -> bool:
    """¿A qué archivo apunta? Obsidian acepta ruta completa o solo el nombre."""
    candidates = {target, f"{target}.md"}
    if candidates & files.keys():
        return True
    # Enlace por nombre de archivo suelto (sin carpeta).
    base = os.path.basename(target)
    for p in files:
        name = os.path.basename(p)
        if name == base or name == f"{base}.md":
            return True
    return False


def main() -> int:
    vault = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_VAULT
    if not os.path.isdir(vault):
        print(f"ABORTA: no existe el vault {vault}", file=sys.stderr)
        return 2

    files = collect(vault)
    pages = {p: v for p, v in files.items() if p.endswith(".md")}

    broken: list[tuple[str, str]] = []
    linked_to: set[str] = set()

    for page, full in sorted(pages.items()):
        with open(full, encoding="utf-8") as fh:
            text = fh.read()
        for target in wikilinks(text):
            if resolve(target, files):
                linked_to.add(os.path.basename(target).removesuffix(".md"))
            else:
                broken.append((page, target))

    orphans = [
        p
        for p in sorted(pages)
        if p.startswith("wiki/")
        and os.path.basename(p).removesuffix(".md") not in linked_to
    ]

    fuentes = {
        os.path.basename(p).removesuffix(".md")
        for p in pages
        if p.startswith("wiki/fuentes/")
    }
    sin_ficha = [
        p
        for p in sorted(files)
        if p.startswith("raw/")
        and p.endswith(".md")
        and os.path.basename(p).removesuffix(".md") not in fuentes
    ]

    print(f"vault: {vault}")
    print(f"  {len(pages)} páginas, {len(files) - len(pages)} adjuntos\n")

    print(f"enlaces rotos: {len(broken)}")
    for page, target in broken:
        print(f"    {page} -> [[{target}]]")

    print(f"\npáginas huérfanas (nadie las enlaza): {len(orphans)}")
    for p in orphans:
        print(f"    {p}")

    print(f"\nfuentes en raw/ sin ficha en wiki/fuentes/: {len(sin_ficha)}")
    for p in sin_ficha:
        print(f"    {p}")

    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
