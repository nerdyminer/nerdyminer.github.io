#!/usr/bin/env python3
"""Genera el orden de navegación anterior/siguiente de las entradas del blog.

El orden de cada sección se deriva del parámetro `number-offset` del front
matter de cada entrada (que ya define su número dentro de la sección), de modo
que la navegación siempre refleja la numeración real y no una lista mantenida a
mano. El resultado se inyecta en `_includes/notes-prev-next.html`, entre los
marcadores NOTES_ORDER_START / NOTES_ORDER_END.

Se ejecuta como hook `pre-render` de Quarto. Sólo usa la librería estándar para
no depender del entorno de Python del build.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INCLUDE = ROOT / "_includes" / "notes-prev-next.html"
CONTENT_DIRS = ("apuntes", "clases")
START = "/* NOTES_ORDER_START */"
END = "/* NOTES_ORDER_END */"

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def read_front_matter(qmd: Path):
    """Devuelve (title, number_offset) o (None, None) si faltan."""
    text = qmd.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None, None
    end = text.find("\n---", 3)
    if end == -1:
        return None, None
    title = None
    offset = None
    for line in text[3:end].splitlines():
        m = re.match(r"\s*title:\s*(.+?)\s*$", line)
        if m and title is None:
            val = m.group(1).strip()
            if len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
                val = val[1:-1]
            title = val
        m = re.match(r"\s*number-offset:\s*(\d+)", line)
        if m and offset is None:
            offset = int(m.group(1))
    return title, offset


def clean_title(title: str) -> str:
    """Quita etiquetas HTML del título para usarlo como texto de enlace."""
    return _WS_RE.sub(" ", _TAG_RE.sub("", title)).strip()


def main() -> None:
    sections: dict[str, list] = {}
    for base in CONTENT_DIRS:
        for qmd in sorted((ROOT / base).rglob("index.qmd")):
            title, offset = read_front_matter(qmd)
            if title is None or offset is None:
                continue
            entry_dir = qmd.parent
            section = str(entry_dir.parent.relative_to(ROOT)).replace("\\", "/")
            href = "/" + str(entry_dir.relative_to(ROOT)).replace("\\", "/") + "/"
            sections.setdefault(section, []).append((offset, clean_title(title), href))

    notes_order = []
    for section in sorted(sections):
        items = sorted(sections[section], key=lambda t: (t[0], t[2]))
        notes_order.append({
            "section": section,
            "items": [{"title": t, "href": h} for (_, t, h) in items],
        })

    payload = json.dumps(notes_order, ensure_ascii=False, indent=4)
    block = f"{START}\n  const notesOrder = {payload};\n  {END}"

    html = INCLUDE.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(html):
        raise SystemExit(f"No se encontraron los marcadores en {INCLUDE}")
    INCLUDE.write_text(pattern.sub(lambda _: block, html), encoding="utf-8")

    total = sum(len(s["items"]) for s in notes_order)
    print(f"notes-order: {total} entradas en {len(notes_order)} secciones")


if __name__ == "__main__":
    main()
