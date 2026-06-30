#!/usr/bin/env python3
"""validate_drawio.py — QA de un .drawio recién generado por el diagramador.

No reemplaza el ojo humano: atrapa los errores mecánicos que arruinan un diagrama
y que cuestan ver a simple vista. Chequea, por archivo:

  ERRORES (rompen el render o el archivo → exit 1):
    - XML mal formado.
    - data-URI de imagen en formato roto (``;base64,`` o ``image/svg``): draw.io
      NO lo renderiza. Debe ser ``data:image/png,<base64>``.
    - edge colgado: source/target que apunta a un id inexistente.

  AVISOS (legibilidad → no fallan, pero conviene revisar):
    - fontSize < 7 (ilegible al abrir).
    - texto que probablemente desborda su caja (y la caja no tiene wrap).
    - vértices que se solapan > 50% (cajas pisadas).
    - página sin contenido / modelo comprimido (no auditable).

Uso:
    python3 validate_drawio.py archivo.drawio [otro.drawio ...]
    python3 validate_drawio.py context/**/*.drawio
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from itertools import combinations
from pathlib import Path

FONT_RE = re.compile(r"fontSize=(\d+(?:\.\d+)?)")
TAG_RE = re.compile(r"<[^>]+>")
BR_RE = re.compile(r"<br\s*/?>", re.I)
BAD_URI_RE = re.compile(r"data:image/(?:png|jpe?g);base64,|data:image/svg", re.I)
DEFAULT_FONT = 12.0
CHAR_W = 0.58          # ancho medio de carácter relativo al fontSize (Helvetica)
OVERLAP_FRAC = 0.50    # fracción del área del menor para marcar solapamiento


def _style_val(style: str, key: str) -> str | None:
    for part in (style or "").split(";"):
        if part.startswith(key + "="):
            return part[len(key) + 1:]
    return None


def _font_size(style: str) -> float:
    m = FONT_RE.search(style or "")
    return float(m.group(1)) if m else DEFAULT_FONT


def _plain_lines(value: str) -> list[str]:
    """value (puede traer HTML) -> líneas de texto plano."""
    if not value:
        return []
    txt = BR_RE.sub("\n", value)
    txt = txt.replace("&#xa;", "\n").replace("&#10;", "\n")
    txt = TAG_RE.sub("", txt)
    txt = (txt.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
              .replace("&quot;", '"').replace("&#39;", "'"))
    return [ln for ln in txt.split("\n")]


def _geom(cell: ET.Element):
    g = cell.find("mxGeometry")
    if g is None:
        return None
    try:
        return (float(g.get("x", "0")), float(g.get("y", "0")),
                float(g.get("width", "0")), float(g.get("height", "0")))
    except ValueError:
        return None


def validate(path: Path) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warns: list[str] = []
    raw = path.read_text(errors="replace")

    # data-URI roto: se detecta sobre el texto crudo (sobrevive aunque el XML parsee)
    if BAD_URI_RE.search(raw):
        errors.append("data-URI de imagen en formato roto (';base64,' o image/svg) — "
                      "draw.io no lo renderiza; usá 'data:image/png,<base64>' (script add_icon.py)")

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        errors.append(f"XML mal formado: {e}")
        return errors, warns, {}

    diagrams = root.findall(".//diagram")
    pages = [d.get("name", f"(página {i+1})") for i, d in enumerate(diagrams)] or ["(sin <diagram>)"]

    cells = root.findall(".//mxCell")
    by_id = {c.get("id"): c for c in cells if c.get("id") is not None}
    parents = {c.get("parent") for c in cells if c.get("parent")}

    vertices = [c for c in cells if c.get("vertex") == "1"]
    edges = [c for c in cells if c.get("edge") == "1"]
    images = [c for c in vertices if "shape=image" in (c.get("style") or "")]
    aws4 = [c for c in vertices if "mxgraph.aws4" in (c.get("style") or "")]

    # modelo comprimido (diagram con texto y sin mxGraphModel) → no auditable
    for d in diagrams:
        if d.find(".//mxCell") is None and (d.text or "").strip():
            warns.append(f"página '{d.get('name','?')}': modelo comprimido/base64, "
                         "no se puede auditar contenido (guardá el .drawio sin comprimir)")

    # edges colgados
    for e in edges:
        for end in ("source", "target"):
            ref = e.get(end)
            if ref and ref not in by_id:
                warns.append(f"edge {e.get('id')}: {end}='{ref}' no existe")

    # posición absoluta resolviendo cadena de parents
    geoms = {c.get("id"): _geom(c) for c in vertices if _geom(c) is not None}
    cache: dict = {}

    def abs_xy(cid):
        if cid in cache:
            return cache[cid]
        g = geoms.get(cid)
        if g is None:
            return (0.0, 0.0)
        p = by_id.get(cid).get("parent") if cid in by_id else None
        px, py = abs_xy(p) if p in geoms else (0.0, 0.0)
        cache[cid] = (px + g[0], py + g[1])
        return cache[cid]

    leaves = []  # (id, x, y, w, h) de vértices que no contienen a otros
    for c in vertices:
        cid = c.get("id")
        g = geoms.get(cid)
        if g is None or cid in parents:   # excluir contenedores/grupos
            continue
        if g[2] <= 0 or g[3] <= 0:
            continue
        ax, ay = abs_xy(cid)
        leaves.append((cid, ax, ay, g[2], g[3], c))

    # legibilidad por vértice hoja
    for cid, ax, ay, w, h, c in leaves:
        style = c.get("style") or ""
        fs = _font_size(style)
        if fs < 7:
            warns.append(f"vértice {cid}: fontSize={fs:g} (ilegible al abrir; mínimo ~7)")
        if "shape=image" in style:
            continue
        lines = [ln for ln in _plain_lines(c.get("value", "")) if ln.strip()]
        if not lines:
            continue
        wrap = "whiteSpace=wrap" in style or "html=1" in style and "overflow" in style
        longest = max(len(ln) for ln in lines)
        est = longest * fs * CHAR_W
        if not wrap and est > w * 1.08:
            warns.append(f"vértice {cid}: texto ~{est:.0f}px no entra en ancho {w:g}px "
                         f"(\"{lines[0][:32]}\"…) — ampliá la caja o usá whiteSpace=wrap")

    # solapamientos entre hojas
    def overlap(a, b):
        _, ax, ay, aw, ah, _ = a
        _, bx, by, bw, bh, _ = b
        ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
        iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
        inter = ix * iy
        if inter <= 0:
            return 0.0
        return inter / min(aw * ah, bw * bh)

    flagged = 0
    for a, b in combinations(leaves, 2):
        if overlap(a, b) > OVERLAP_FRAC:
            flagged += 1
            if flagged <= 8:
                warns.append(f"solapamiento: vértices {a[0]} y {b[0]} se pisan "
                             f">{int(OVERLAP_FRAC*100)}%")
    if flagged > 8:
        warns.append(f"... y {flagged - 8} solapamientos más")

    metrics = {
        "páginas": len(diagrams), "nombres": pages,
        "vértices": len(vertices), "edges": len(edges),
        "imágenes": len(images), "íconos aws4": len(aws4),
    }
    return errors, warns, metrics


def main(argv: list[str]) -> int:
    if not argv:
        print("uso: validate_drawio.py archivo.drawio [...]", file=sys.stderr)
        return 2
    paths = [Path(p) for p in argv]
    rc = 0
    for path in paths:
        print(f"\n=== {path} ===")
        if not path.exists():
            print("  ERROR: no existe")
            rc = 1
            continue
        errors, warns, metrics = validate(path)
        if metrics:
            print("  resumen: " + " · ".join(f"{k}={v}" for k, v in metrics.items()
                                              if k != "nombres"))
            print("  páginas: " + ", ".join(metrics["nombres"]))
        for e in errors:
            print(f"  ✗ ERROR: {e}")
        for w in warns:
            print(f"  ⚠ aviso: {w}")
        if not errors and not warns:
            print("  ✓ sin errores ni avisos")
        if errors:
            rc = 1
    print()
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
