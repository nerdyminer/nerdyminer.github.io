"""Genera el explorador estático desde los archivos reales del proyecto."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
OUTPUT = ROOT / "source" / "index.html"

FILES = [
    ("Entorno", "README.md", "Propósito, ejecución, privacidad y arquitectura."),
    ("Entorno", "pyproject.toml", "Dependencias, paquete y herramientas de calidad."),
    ("Configuración", "conf/public.toml", "Geometría y parámetros del escenario sintético."),
    ("Contratos", "src/stockpile_ca/contracts.py", "Modelos estrictos, inmutables y relacionales."),
    ("Contratos", "src/stockpile_ca/config.py", "Carga TOML y normalización de representación."),
    ("Datos", "src/stockpile_ca/data.py", "Lectura determinista y plan de Polars."),
    ("Dominio", "src/stockpile_ca/domain/segregation.py", "Separación conservativa de tamaños."),
    ("Dominio", "src/stockpile_ca/domain/kernel.py", "Estado, formación, descarga y superficie."),
    (
        "Validación",
        "src/stockpile_ca/domain/reconciliation.py",
        "Bias, MAE y RMSE como funciones puras.",
    ),
    ("Dagster", "src/stockpile_ca/defs/assets.py", "Activos, replay y asset checks."),
    ("Dagster", "src/stockpile_ca/definitions.py", "Composición descubrible por el orquestador."),
    (
        "Dagster",
        "scripts/build_dagster_snapshot.py",
        "Exportación web del Asset Graph desde Definitions.",
    ),
    ("Pruebas", "tests/test_contracts.py", "Coherencia de configuración y centro único."),
    ("Pruebas", "tests/test_data.py", "Determinismo, completitud y fechas futuras."),
    ("Pruebas", "tests/test_domain.py", "Conservación de volumen y tamaño."),
    ("Pruebas", "tests/test_dagster_graph.py", "Linaje y checks del Asset Graph público."),
    ("Pruebas", "tests/test_anonymisation.py", "Barrera ejecutable contra identificadores."),
    ("Visor", "app-src/src/frames.ts", "Contrato y decodificación de 61 días binarios públicos."),
    ("Visor", "app-src/src/App.tsx", "Estado compartido y composición de vistas."),
    (
        "Visor",
        "app-src/src/components/Stockpile3D.tsx",
        "Proyección y cámara orbitable sobre canvas.",
    ),
    ("Visor", "app-src/src/components/OrthogonalViews.tsx", "Planta y cortes verticales."),
    ("Visor", "app-src/src/components/HeightReconciliation.tsx", "Altura y balance no modelado."),
    ("Visor", "app-src/src/components/SizeReconciliation.tsx", "PSD medida y P80 simulado."),
]


def language(path: str) -> str:
    return Path(path).suffix.lstrip(".") or "text"


def build() -> None:
    entries = [
        {
            "section": section,
            "path": path,
            "description": description,
            "language": language(path),
            "source": (ROOT / path).read_text(encoding="utf-8"),
        }
        for section, path, description in FILES
    ]
    payload = json.dumps(entries, ensure_ascii=False).replace("</", "<\\/")
    document = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Explorador de código · Stockpile CA</title>
<style>
:root{{--bg:#f6f4ef;--panel:#fff;--ink:#203035;--muted:#66757a;--line:#d9dfdf;--accent:#7d2b6a;--teal:#1c434b;--code:#132428;--code-ink:#e9f0ed}}
*{{box-sizing:border-box}}html,body{{height:100%;overflow:hidden}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,-apple-system,sans-serif}}
.app{{display:grid;grid-template-columns:310px minmax(0,1fr);height:100vh;height:100dvh;overflow:hidden}}aside{{height:100%;min-width:0;min-height:0;overflow:hidden;background:var(--panel);border-right:1px solid var(--line);display:flex;flex-direction:column}}
.aside-head{{padding:18px;border-bottom:1px solid var(--line)}}h1{{font:700 20px/1.15 Georgia,serif;margin:0 0 6px;color:var(--teal)}}.aside-head p{{margin:0 0 12px;color:var(--muted)}}
input{{width:100%;padding:9px 11px;border:1px solid var(--line);border-radius:7px}}nav{{height:0;min-height:0;flex:1 1 0;overflow-x:hidden;overflow-y:scroll;overscroll-behavior:contain;padding:8px;scrollbar-gutter:stable;scrollbar-color:#a57a9a #f2efeb;scrollbar-width:thin}}
.step{{display:block;width:100%;text-align:left;border:0;border-radius:7px;background:transparent;padding:9px 10px;color:var(--ink);cursor:pointer}}.step:hover{{background:#f1e8ef}}.step.active{{background:#ead9e6;color:#4c163f}}.step small{{display:block;color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.07em}}
main{{min-width:0;min-height:0;overflow:hidden;display:flex;flex-direction:column}}header{{flex:0 0 auto;padding:16px 20px;background:var(--panel);border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:18px;align-items:center}}.meta{{min-width:0}}.eyebrow{{color:var(--accent);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.09em}}h2{{margin:2px 0;font:700 18px/1.2 Georgia,serif}}.description{{color:var(--muted)}}.actions{{display:flex;gap:8px}}button{{padding:8px 11px;border:1px solid var(--line);border-radius:7px;background:#fff;cursor:pointer}}button:disabled{{opacity:.35}}
.code-wrap{{min-height:0;flex:1 1 0;overflow-x:auto;overflow-y:scroll;overscroll-behavior:contain;background:var(--code);scrollbar-gutter:stable;scrollbar-color:#5a7b7e #0d1b1e;scrollbar-width:thin}}nav::-webkit-scrollbar,.code-wrap::-webkit-scrollbar{{width:10px;height:10px}}nav::-webkit-scrollbar-track{{background:#f2efeb}}nav::-webkit-scrollbar-thumb{{border:2px solid #f2efeb;border-radius:999px;background:#a57a9a}}.code-wrap::-webkit-scrollbar-track{{background:#0d1b1e}}.code-wrap::-webkit-scrollbar-thumb{{border:2px solid #0d1b1e;border-radius:999px;background:#5a7b7e}}pre{{margin:0;padding:22px;min-width:max-content;color:var(--code-ink);font:12.5px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace;tab-size:4;white-space:pre}}.counter{{font-variant-numeric:tabular-nums;color:var(--muted);white-space:nowrap}}
@media(max-width:780px){{.app{{grid-template-columns:1fr;grid-template-rows:minmax(220px,40dvh) minmax(0,1fr)}}aside{{height:auto;border-right:0;border-bottom:1px solid var(--line)}}main{{height:auto;min-height:0}}header{{align-items:flex-start;flex-direction:column}}}}
</style></head><body><div class="app"><aside><div class="aside-head"><h1>Stockpile CA</h1><p>Lectura guiada del repositorio público.</p><input id="search" type="search" placeholder="Filtrar archivos…"></div><nav id="steps" aria-label="Archivos del proyecto" tabindex="0"></nav></aside>
<main><header><div class="meta"><div id="section" class="eyebrow"></div><h2 id="path"></h2><div id="description" class="description"></div></div><div class="actions"><span id="counter" class="counter"></span><button id="previous" aria-label="Anterior">←</button><button id="next" aria-label="Siguiente">→</button><button id="copy">Copiar</button></div></header><div class="code-wrap" role="region" aria-label="Contenido del archivo seleccionado" tabindex="0"><pre><code id="source"></code></pre></div></main></div>
<script>const FILES={payload};const nav=document.getElementById('steps'),source=document.getElementById('source'),search=document.getElementById('search');let current=0;
function esc(s){{return s.replace(/[&<>]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c]))}}
function visible(){{const q=search.value.trim().toLowerCase();return FILES.map((f,i)=>[f,i]).filter(([f])=>!q||`${{f.section}} ${{f.path}} ${{f.description}}`.toLowerCase().includes(q)).map(([,i])=>i)}}
function renderNav(){{nav.innerHTML='';visible().forEach(i=>{{const f=FILES[i],b=document.createElement('button');b.className='step'+(i===current?' active':'');b.innerHTML=`<small>${{String(i+1).padStart(2,'0')}} · ${{esc(f.section)}}</small>${{esc(f.path)}}`;b.onclick=()=>show(i);nav.appendChild(b)}})}}
function show(i){{current=Math.max(0,Math.min(FILES.length-1,i));const f=FILES[current];document.getElementById('section').textContent=f.section;document.getElementById('path').textContent=f.path;document.getElementById('description').textContent=f.description;document.getElementById('counter').textContent=`${{current+1}} / ${{FILES.length}}`;source.innerHTML=esc(f.source);document.getElementById('previous').disabled=current===0;document.getElementById('next').disabled=current===FILES.length-1;renderNav();document.querySelector('.code-wrap').scrollTop=0}}
search.oninput=renderNav;document.getElementById('previous').onclick=()=>show(current-1);document.getElementById('next').onclick=()=>show(current+1);document.getElementById('copy').onclick=async e=>{{await navigator.clipboard.writeText(FILES[current].source);e.target.textContent='Copiado';setTimeout(()=>e.target.textContent='Copiar',900)}};document.addEventListener('keydown',e=>{{if(e.target===search)return;if(e.key==='ArrowLeft')show(current-1);if(e.key==='ArrowRight')show(current+1)}});show(0);</script></body></html>"""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(document, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)} with {len(entries)} files")


if __name__ == "__main__":
    build()
