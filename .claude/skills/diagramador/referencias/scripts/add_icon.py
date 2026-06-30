#!/usr/bin/env python3
"""add_icon.py — mantenimiento de la librería de íconos del diagramador.

Resuelve EL detalle crítico del skill de forma determinística: el data-URI que
draw.io necesita es ``data:image/png,<base64>`` — **con coma y SIN ``;base64``**.
El formato ``data:image/png;base64,…`` se rompe porque draw.io parte el atributo
``image=`` por el ``;`` que separa estilos. Este script siempre emite el formato
correcto, así nadie lo arma a mano.

Uso
----
    # Agregar / actualizar un motor (acepta PNG o SVG; SVG se rasteriza):
    python3 add_icon.py <motor> <ruta-imagen> [--size 256] [--no-copy]

    # Regenerar _uris.json desde TODOS los PNG presentes en iconos/:
    python3 add_icon.py --rebuild [--size 256]

    # Verificar que cada URI esté en el formato correcto y tenga su PNG:
    python3 add_icon.py --check

La carpeta de íconos se resuelve relativa a este script
(``../iconos``), no al directorio de trabajo.
"""
from __future__ import annotations

import argparse
import base64
import json
import shutil
import subprocess
import sys
from pathlib import Path

ICONS_DIR = (Path(__file__).resolve().parent.parent / "iconos").resolve()
URIS_JSON = ICONS_DIR / "_uris.json"
PREFIX = "data:image/png,"  # coma, sin ;base64 — NO TOCAR


def _die(msg: str) -> "None":
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(1)


def png_to_uri(png: Path) -> str:
    """PNG en disco -> data-URI en el formato que draw.io sí renderiza."""
    b64 = base64.b64encode(png.read_bytes()).decode("ascii")
    return PREFIX + b64


def svg_to_png(svg: Path, size: int) -> Path:
    """Rasteriza un SVG a PNG probando los backends disponibles.

    Orden: rsvg-convert, cairosvg, inkscape, qlmanage (macOS). El PNG se deja
    junto al SVG (mismo nombre, extensión .png). Si ninguno está instalado,
    aborta pidiendo un PNG.
    """
    out = svg.with_suffix(".png")
    attempts = [
        ["rsvg-convert", "-w", str(size), "-h", str(size), str(svg), "-o", str(out)],
        ["cairosvg", str(svg), "-o", str(out), "-W", str(size), "-H", str(size)],
        ["inkscape", str(svg), "--export-type=png", f"--export-filename={out}",
         f"--export-width={size}", f"--export-height={size}"],
    ]
    for cmd in attempts:
        if shutil.which(cmd[0]) is None:
            continue
        if subprocess.run(cmd, capture_output=True).returncode == 0 and out.exists():
            return out
    # qlmanage (macOS) deja <archivo>.svg.png en el outdir
    if shutil.which("qlmanage"):
        subprocess.run(["qlmanage", "-t", "-s", str(size), "-o", str(svg.parent), str(svg)],
                       capture_output=True)
        ql = svg.parent / (svg.name + ".png")
        if ql.exists():
            ql.replace(out)
            return out
    _die(f"no pude rasterizar {svg.name}: instalá rsvg-convert / cairosvg / inkscape, "
         f"o pasá directamente un PNG.")


def load_uris() -> dict:
    return json.loads(URIS_JSON.read_text()) if URIS_JSON.exists() else {}


def save_uris(uris: dict) -> "None":
    # claves ordenadas, una entrada por línea: diffs legibles en git
    URIS_JSON.write_text(json.dumps(dict(sorted(uris.items())), ensure_ascii=False, indent=2) + "\n")


def cmd_add(motor: str, src: str, size: int, copy: bool) -> "None":
    src_path = Path(src).expanduser().resolve()
    if not src_path.exists():
        _die(f"no existe la imagen: {src_path}")

    if src_path.suffix.lower() == ".svg":
        if copy:
            dst_svg = ICONS_DIR / f"{motor}.svg"
            if src_path != dst_svg:
                shutil.copy2(src_path, dst_svg)
            src_path = dst_svg
        png = svg_to_png(src_path, size)
    elif src_path.suffix.lower() == ".png":
        png = ICONS_DIR / f"{motor}.png"
        if copy and src_path != png:
            shutil.copy2(src_path, png)
            png = png
        else:
            png = src_path
    else:
        _die(f"formato no soportado: {src_path.suffix} (usá .png o .svg)")

    uris = load_uris()
    uris[motor] = png_to_uri(png)
    save_uris(uris)
    print(f"ok: '{motor}' actualizado en _uris.json ({len(uris[motor])} chars) desde {png.name}")


def cmd_rebuild(size: int) -> "None":
    pngs = sorted(p for p in ICONS_DIR.glob("*.png") if not p.name.startswith("_"))
    if not pngs:
        # intentar rasterizar SVGs si no hay PNGs
        for svg in sorted(ICONS_DIR.glob("*.svg")):
            svg_to_png(svg, size)
        pngs = sorted(p for p in ICONS_DIR.glob("*.png") if not p.name.startswith("_"))
    uris = {p.stem: png_to_uri(p) for p in pngs}
    save_uris(uris)
    print(f"ok: _uris.json regenerado con {len(uris)} motores: {', '.join(uris)}")


def cmd_check() -> int:
    uris = load_uris()
    problems = []
    for motor, uri in uris.items():
        if uri.startswith("data:image/png;base64,"):
            problems.append(f"{motor}: usa ';base64,' — draw.io lo rompe (debe ser 'data:image/png,')")
        elif not uri.startswith(PREFIX):
            problems.append(f"{motor}: prefijo inesperado '{uri[:24]}…' (esperado '{PREFIX}')")
        if not (ICONS_DIR / f"{motor}.png").exists():
            problems.append(f"{motor}: falta {motor}.png en iconos/")
    if problems:
        print("PROBLEMAS:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"ok: {len(uris)} motores, todos en formato correcto y con su PNG.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Mantenimiento de la librería de íconos del diagramador.")
    ap.add_argument("motor", nargs="?", help="nombre del motor (ej: clickhouse)")
    ap.add_argument("imagen", nargs="?", help="ruta a la imagen PNG o SVG")
    ap.add_argument("--size", type=int, default=256, help="tamaño de rasterizado para SVG (def: 256)")
    ap.add_argument("--no-copy", action="store_true", help="no copiar la imagen fuente a iconos/")
    ap.add_argument("--rebuild", action="store_true", help="regenerar _uris.json desde los PNG presentes")
    ap.add_argument("--check", action="store_true", help="verificar formato de todas las URIs")
    a = ap.parse_args()

    if a.check:
        return cmd_check()
    if a.rebuild:
        cmd_rebuild(a.size)
        return 0
    if not a.motor or not a.imagen:
        ap.error("pasá <motor> <imagen>, o usá --rebuild / --check")
    cmd_add(a.motor, a.imagen, a.size, copy=not a.no_copy)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
