"""Normalizacion deterministica de categorias / areas de negocio.

Referencia compartida entre:
  - El generador de keywords (LLM Bedrock + post-process del equipo IA).
  - El matcher de joyas-priorizer (PySpark / EMR).
  - El agente, si decide normalizar nombres antes del envio.

Cualquier divergencia entre estas tres puntas rompe el match. Cambios a este
modulo requieren bump de `normalize_version` y reprocesamiento.

Regla (aplicada en orden):
  1. lowercase
  2. strip diacriticos (NFKD -> quitar tildes y enie)
  3. quitar digitos 0-9
  4. quitar todo lo que no sea a-z o espacio
  5. quitar tokens 100% romanos (i, v, x, l, c, d, m)
  6. colapsar espacios y trim

Uso como libreria:
    from normalize_category import normalize
    normalize("Plan Estrategico Quinquenal 2026")  # -> "plan estrategico quinquenal"

Uso como CLI:
    python normalize_category.py "Plan Estrategico Quinquenal 2026"
    echo "Estrategia & Planeacion" | python normalize_category.py -
"""
from __future__ import annotations

import re
import sys
import unicodedata

ROMAN = set("ivxlcdm")

_DIGIT_RE = re.compile(r"[0-9]+")
_NON_LETTER_RE = re.compile(r"[^a-z\s]+")


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize(raw: str) -> str:
    text = _strip_accents(raw).lower()
    text = _DIGIT_RE.sub(" ", text)
    text = _NON_LETTER_RE.sub(" ", text)
    tokens = [t for t in text.split() if not (t and all(ch in ROMAN for ch in t))]
    return " ".join(tokens)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("uso: python normalize_category.py <texto> | -", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == "-":
        for line in sys.stdin:
            print(normalize(line.rstrip("\n")))
    else:
        print(normalize(" ".join(sys.argv[1:])))
