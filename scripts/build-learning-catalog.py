#!/usr/bin/env python3
"""Construye el catálogo pedagógico público de NerdyMiner.

El catálogo no intenta convertir páginas de índice, recursos auxiliares o
contenidos todavía en preparación en lecciones. Sólo clasifica material
sustantivo y capítulos de proyectos publicados. Las reglas editoriales quedan
centralizadas aquí para que nivel, duración y prerrequisitos sean consistentes
en la portada, las rutas y el contexto que aparece dentro de cada lectura.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "learning-content.json"
CONTENT_ROOTS = ("articulos", "apuntes", "clases", "proyectos")
RESOURCE_DIRS = {"datasets", "images", "media"}

TAG_RE = re.compile(r"<[^>]+>")
LINK_RE = re.compile(r"\[([^]]+)]\([^)]+\)")
WORD_RE = re.compile(r"\b[\wáéíóúüñÁÉÍÓÚÜÑ]+\b")
CODE_RE = re.compile(r"```.*?```", re.DOTALL)


def split_document(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text

    meta: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, text[end + 4 :]


def clean_inline(value: str) -> str:
    value = LINK_RE.sub(r"\1", value)
    value = TAG_RE.sub("", value)
    value = value.replace("**", "").replace("*", "")
    return re.sub(r"\s+", " ", value).strip()


def word_count(body: str) -> int:
    prose = CODE_RE.sub("", body)
    prose = TAG_RE.sub(" ", prose)
    return len(WORD_RE.findall(prose))


def code_block_count(body: str) -> int:
    return len(re.findall(r"^```", body, re.MULTILINE)) // 2


def estimate_minutes(words: int, code_blocks: int) -> int:
    # La lectura técnica es más lenta que la lectura editorial. Cada bloque de
    # código agrega tiempo de inspección o reproducción, aunque sea breve.
    raw = words / 170 + code_blocks * 1.35
    return max(10, int(math.ceil(raw / 5) * 5))


def format_duration(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} min"
    hours, remainder = divmod(minutes, 60)
    if remainder == 0:
        return f"{hours} h"
    return f"{hours} h {remainder} min"


def infer_kind(path: Path) -> str:
    root = path.relative_to(ROOT).parts[0]
    return {
        "articulos": "Artículo",
        "apuntes": "Apunte",
        "clases": "Clase",
        "proyectos": "Proyecto",
    }[root]


def infer_level(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()

    if rel.startswith("proyectos/"):
        return "Avanzado"
    if "tensores-y-variedades" in rel:
        return "Avanzado"
    if any(key in rel for key in (
        "descomposiciones-matriciales",
        "introduccion-a-las-formas",
        "cadenas-de-markov",
        "introduccion-a-la-teoria-de-la-informacion",
        "optimizacion-de-grafos",
        "optimizacion-aplicada-al-aprendizaje-automatico",
        "optimizacion-de-tipo-black-box",
        "maquinas-de-soporte-vectorial",
        "modelos-lineales-regularizados-bayesianos-y-generalizados",
        "importancia-de-variables",
        "modelos-de-ensamble",
        "seleccion-y-evaluacion-de-modelos",
        "jb-jc-modeling",
        "pit-final-3d",
    )):
        return "Avanzado"
    if "aplicaciones-del-calculo-diferencial" in rel:
        return "Intermedio"
    if any(key in rel for key in (
        "espacios-vectoriales",
        "bases-y-dimension",
        "transformaciones-lineales",
        "calculo-diferencial",
        "probabilidad-clasica",
        "introduccion-a-numpy",
        "operatoria-en-numpy",
        "broadcasting-y-agregacion",
        "comparacion-ordenamiento-y-reemplazo",
        "introduccion-rapida-a-pandas",
        "tipos-de-datos-en-pandas",
        "manipulacion-de-series",
        "introduccion-a-scikit-learn",
        "introduccion-algoritmos-aprendizaje",
        "presentacion",
    )):
        return "Inicial"
    return "Intermedio"


def infer_route(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if any(key in rel for key in ("numpy", "pandas")):
        return "Python para analizar datos"
    if any(key in rel for key in (
        "estructuras-lineales",
        "calculo-incertidumbre-y-optimizacion",
        "tensores-y-variedades",
    )):
        return "Matemáticas para modelar"
    if "clases/machine-learning" in rel:
        return "Machine learning con criterio"
    if any(key in rel for key in ("pit-final", "modelos-lane-y-vickers")):
        return "Optimización y decisiones mineras"
    if "grafos-e-informacion" in rel:
        return "Grafos, información y optimización"
    if "bayesian-tph-forecasting" in rel:
        return "Forecasting Bayesiano operacional"
    if "stockpile-cellular-automata" in rel:
        return "Digital twin de stockpile"
    if "jb-jc-modeling" in rel:
        return "Modelamiento de procesos mineralúrgicos"
    return "Lecturas aplicadas"


def infer_prerequisite(level: str, route: str) -> str:
    if level == "Inicial":
        if route == "Python para analizar datos":
            return "Python básico"
        return "Ninguno"
    if route == "Machine learning con criterio":
        return "Python, álgebra lineal y probabilidad básica"
    if route in {"Forecasting Bayesiano operacional", "Digital twin de stockpile"}:
        return "Python intermedio y fundamentos de modelamiento"
    if level == "Avanzado":
        return "Fundamentos matemáticos del área"
    return "Fundamentos introductorios del tema"


def infer_sequence(path: Path, meta: dict[str, str], route: str) -> int:
    rel = path.relative_to(ROOT).as_posix()
    offset_match = re.match(r"\d+", meta.get("number-offset", ""))
    offset = int(offset_match.group()) if offset_match else 50

    if route == "Python para analizar datos":
        return (0 if "numpy" in rel else 100) + offset
    if route == "Matemáticas para modelar":
        if "estructuras-lineales" in rel:
            return offset
        if "calculo-incertidumbre-y-optimizacion" in rel:
            return 100 + offset
        return 200 + offset
    if route == "Machine learning con criterio":
        if "modelos-lineales" in rel:
            return offset
        if "modelos-no-lineales" in rel:
            return 100 + offset
        return 200 + offset
    if route == "Optimización y decisiones mineras":
        if "pit-final/index" in rel:
            return 1
        if "pit-final-3d" in rel:
            return 2
        return 3
    if rel.startswith("proyectos/"):
        if path.name == "index.qmd":
            return 0
        chapter_match = re.match(r"(\d+)-", path.stem)
        return int(chapter_match.group(1)) if chapter_match else 99
    return offset


def infer_summary(meta: dict[str, str], body: str) -> str:
    if meta.get("description"):
        return clean_inline(meta["description"])

    # La idea central suele ser la mejor declaración pedagógica disponible.
    match = re.search(
        r"## Idea central\s+(.*?)(?:\n\s*:::|\n\s*## )",
        body,
        re.DOTALL | re.IGNORECASE,
    )
    if match:
        paragraph = clean_inline(match.group(1))
        if paragraph:
            return paragraph

    for paragraph in re.split(r"\n\s*\n", CODE_RE.sub("", body)):
        value = clean_inline(paragraph)
        if value and not value.startswith(("#", ":::")):
            return value
    return "Lectura técnica de NerdyMiner."


def published_content(path: Path, words: int) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in RESOURCE_DIRS for part in rel.parts):
        return False
    if rel.as_posix() in {
        "articulos/index.qmd",
        "apuntes/index.qmd",
        "clases/index.qmd",
        "proyectos/index.qmd",
    }:
        return False
    if rel.parts[0] == "proyectos":
        return len(rel.parts) >= 3
    if path.name != "index.qmd":
        return False
    return words >= 1000


def item_for(path: Path) -> dict[str, object] | None:
    text = path.read_text(encoding="utf-8")
    meta, body = split_document(text)
    words = word_count(body)
    if not published_content(path, words):
        return None

    title = clean_inline(meta.get("title", path.parent.name.replace("-", " ").title()))
    blocks = code_block_count(body)
    minutes = estimate_minutes(words, blocks)
    level = infer_level(path)
    route = infer_route(path)
    rel_path = path.relative_to(ROOT)
    rel_parent = rel_path.parent.as_posix()
    if path.name == "index.qmd":
        url = f"/{rel_parent}/"
    else:
        url = f"/{rel_parent}/{path.stem}.html"

    return {
        "source": path.relative_to(ROOT).as_posix(),
        "url": url,
        "title": title,
        "kind": infer_kind(path),
        "level": level,
        "estimatedMinutes": minutes,
        "estimatedTime": format_duration(minutes),
        "route": route,
        "sequence": infer_sequence(path, meta, route),
        "prerequisite": infer_prerequisite(level, route),
        "summary": infer_summary(meta, body),
    }


def main() -> None:
    items: list[dict[str, object]] = []
    for root_name in CONTENT_ROOTS:
        for path in sorted((ROOT / root_name).rglob("*.qmd")):
            item = item_for(path)
            if item:
                items.append(item)

    payload = {
        "schemaVersion": 1,
        "methodology": {
            "levels": {
                "Inicial": "No presupone dominio formal del tema; puede requerir Python básico cuando hay código.",
                "Intermedio": "Requiere fundamentos introductorios y combina conceptos con aplicación.",
                "Avanzado": "Integra formalismo, decisiones metodológicas o una implementación extensa.",
            },
            "timeEstimate": "Lectura técnica a 170 palabras por minuto más tiempo de inspección para cada bloque de código.",
        },
        "items": items,
    }
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"learning-catalog: {len(items)} lecturas evaluadas")


if __name__ == "__main__":
    main()
