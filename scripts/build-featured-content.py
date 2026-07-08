#!/usr/bin/env python3
"""Build the random featured-content pool for the homepage."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "featured-content.json"


KIND_CONFIG = {
    "articulos": {
        "kind": "articulo",
        "label": "Artículo",
        "roots": [ROOT / "articulos"],
        "exclude": {ROOT / "articulos" / "index.qmd"},
    },
    "apuntes": {
        "kind": "apunte",
        "label": "Apunte",
        "roots": [ROOT / "apuntes"],
        "exclude": {ROOT / "apuntes" / "index.qmd"},
    },
    "clases": {
        "kind": "clase",
        "label": "Clase",
        "roots": [ROOT / "clases"],
        "exclude": {ROOT / "clases" / "index.qmd"},
    },
}


INDEX_MARKERS = (
    "class-topic-card",
    "class-topic-grid",
    "notes-card",
    "notes-grid",
)


PLACEHOLDER_MARKERS = (
    "construction-page",
    "en construcción",
    "en construccion",
    "esta clase está en preparación",
    "esta clase esta en preparacion",
    "esta ruta está tomando forma",
    "esta ruta esta tomando forma",
    "placeholder",
    "próximamente",
    "proximamente",
)


EXCLUDED_ENTRY_DIRS = {
    "presentacion",
}


SLUG_LABELS = {
    "aplicaciones-miscelaneas": "Aplicaciones misceláneas",
    "aprendizaje-no-supervisado": "Aprendizaje no supervisado",
    "aprendizaje-supervisado": "Aprendizaje supervisado",
    "articulos": "Artículos",
    "calculo-incertidumbre-y-optimizacion": "Cálculo · Incertidumbre · Optimización",
    "clases": "Clases",
    "computacion-cientifica-en-python": "Computación científica",
    "computacion-vectorizada-y-arreglos-con-numpy": "Numpy",
    "data-analytics": "Data Analytics",
    "deep-learning": "Deep Learning",
    "estructuras-lineales": "Álgebra lineal",
    "grafos-e-informacion": "Grafos · Información",
    "introduccion-al-analisis-de-datos-en-python": "Análisis de datos en Python",
    "jb-jc-modeling": "Minería · Molienda",
    "machine-learning": "Machine Learning",
    "manipulacion-tabular-y-analisis-con-pandas": "Pandas",
    "modelos-lineales": "Modelos lineales",
    "modelos-no-lineales": "Modelos no lineales",
    "pit-final": "Minería · Optimización",
    "pit-final-3d": "Minería · Optimización 3D",
    "seleccion-de-variables-metricas-y-tuning": "Selección · Métricas · Tuning",
    "series-de-tiempo": "Series de tiempo",
    "tensores-y-variedades": "Tensores · Variedades",
    "visualizacion-de-datos": "Visualización",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text

    _, raw_meta, body = text.split("---", 2)
    meta: dict[str, str] = {}

    for line in raw_meta.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip('"').strip("'")
        meta[key.strip()] = value

    return meta, body


def clean_inline(text: str) -> str:
    text = re.sub(r"\*\*<font color='[^']+'>(.*?)</font>\*\*", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\[(.*?)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\{[^}]*\}", "", text)
    text = text.replace("**", "").replace("*", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def infer_title(meta: dict[str, str], body: str, path: Path) -> str:
    if meta.get("title"):
        return clean_inline(meta["title"])

    for line in body.splitlines():
        if line.startswith("# "):
            return clean_inline(line.lstrip("# "))

    return path.parent.name.replace("-", " ").title()


def infer_summary(meta: dict[str, str], body: str) -> str:
    def truncate(summary: str) -> str:
        if len(summary) <= 145:
            return summary
        return summary[:142].rsplit(" ", 1)[0] + "..."

    if meta.get("description"):
        return truncate(clean_inline(meta["description"]))

    in_code = False
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not line or line.startswith(("---", "#", ":::", "<div", "</div")):
            continue
        if line.startswith(("-", ":::")):
            continue
        summary = clean_inline(line)
        return truncate(summary)

    return "Contenido técnico del blog NerdyMiner."


def prettify_slug(slug: str) -> str:
    if slug in SLUG_LABELS:
        return SLUG_LABELS[slug]
    return slug.replace("-", " ").title()


def infer_topics(path: Path, kind_label: str) -> str:
    parts = path.relative_to(ROOT).parts[:-1]
    topics = [kind_label]
    if parts[0] == "clases":
        topic_parts = parts[1:3]
    else:
        topic_parts = parts[1:2]

    for part in topic_parts:
        topic = prettify_slug(part)
        if topic not in topics:
            topics.append(topic)
    return " · ".join(topics)


def url_for(path: Path) -> str:
    rel_parent = path.relative_to(ROOT).parent
    return "/" + rel_parent.as_posix().strip("/") + "/"


def is_listing_page(text: str, path: Path, kind_key: str) -> bool:
    if kind_key == "articulos":
        return False

    if any(marker in text for marker in INDEX_MARKERS):
        return True

    depth = len(path.relative_to(ROOT).parts)
    if kind_key == "clases" and depth <= 3:
        return True

    return False


def is_placeholder_page(text: str) -> bool:
    meta, body = frontmatter(text)
    if meta.get("draft", "").lower() in {"true", "yes", "1"}:
        return True

    header = clean_inline("\n".join(body.splitlines()[:45])).lower()
    return any(marker in header for marker in PLACEHOLDER_MARKERS)


def collect(kind_key: str) -> list[dict[str, str]]:
    config = KIND_CONFIG[kind_key]
    entries: list[dict[str, str]] = []

    for root in config["roots"]:
        for path in sorted(root.rglob("index.qmd")):
            if path in config["exclude"]:
                continue
            if path.parent.name in EXCLUDED_ENTRY_DIRS:
                continue

            text = read_text(path)
            if is_listing_page(text, path, kind_key):
                continue
            if is_placeholder_page(text):
                continue

            meta, body = frontmatter(text)
            title = infer_title(meta, body, path)
            if not title:
                continue

            entries.append(
                {
                    "kind": config["kind"],
                    "meta": infer_topics(path, config["label"]),
                    "title": title,
                    "summary": infer_summary(meta, body),
                    "url": url_for(path),
                }
            )

    return entries


def main() -> None:
    content = {config["kind"]: collect(key) for key, config in KIND_CONFIG.items()}
    OUTPUT.write_text(
        json.dumps(content, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
