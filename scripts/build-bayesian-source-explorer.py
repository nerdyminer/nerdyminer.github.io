"""
Genera un explorador estático y secuencial del código del proyecto Bayesiano.
"""

from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = REPOSITORY_ROOT / "proyectos" / "bayesian-tph-forecasting"
OUTPUT_PATH = PROJECT_ROOT / "source" / "index.html"

SOURCE_STEPS = [
    ("Inicio", "README.md", "Propósito, instalación y comandos reproducibles."),
    ("Inicio", "DATA_PROVENANCE.md", "Procedencia y salvaguardas de los datos públicos."),
    ("Entorno", "pyproject.toml", "Dependencias, metadatos y herramientas del paquete."),
    ("Configuración", "conf/base/parameters.yml", "Supuestos y políticas ajustables."),
    ("Configuración", "conf/base/catalog.yml", "Entradas, artefactos y capas de datos."),
    ("Configuración", "conf/base/logging.yml", "Comportamiento de los registros de ejecución."),
    ("Configuración", "conf/test/parameters.yml", "Sobrescrituras de bajo costo para pruebas."),
    (
        "Datos sintéticos",
        "scripts/generate_public_synthetic_data.py",
        "Generador reproducible de los contratos públicos ficticios.",
    ),
    ("Paquete", "src/bayesian_tph_forecasting/__init__.py", "Identidad y versión del paquete."),
    ("Paquete", "src/bayesian_tph_forecasting/__main__.py", "Punto de entrada de la CLI."),
    ("Paquete", "src/bayesian_tph_forecasting/settings.py", "Carga global de configuración."),
    (
        "Paquete",
        "src/bayesian_tph_forecasting/pipelines/__init__.py",
        "Espacio de nombres de las pipelines modulares.",
    ),
    (
        "Persistencia",
        "src/bayesian_tph_forecasting/datasets/__init__.py",
        "Espacio de nombres de los datasets personalizados.",
    ),
    (
        "Persistencia",
        "src/bayesian_tph_forecasting/datasets/inference_data_dataset.py",
        "Adaptador NetCDF para el posterior de ArviZ.",
    ),
    (
        "Ingeniería de datos",
        "src/bayesian_tph_forecasting/pipelines/data_engineering/__init__.py",
        "Interfaz pública de la pipeline de ingeniería de datos.",
    ),
    (
        "Ingeniería de datos",
        "src/bayesian_tph_forecasting/pipelines/data_engineering/pipeline.py",
        "Declaración de entradas, nodos y salidas de la primera pipeline.",
    ),
    (
        "Ingeniería de datos",
        "src/bayesian_tph_forecasting/pipelines/data_engineering/nodes.py",
        "Limpieza, agregación operacional y contexto espacial.",
    ),
    (
        "Ciencia de datos",
        "src/bayesian_tph_forecasting/pipelines/data_science/__init__.py",
        "Interfaz pública de la pipeline de ciencia de datos.",
    ),
    (
        "Ciencia de datos",
        "src/bayesian_tph_forecasting/pipelines/data_science/pipeline.py",
        "Declaración de firmas geológicas y contrato modelable.",
    ),
    (
        "Ciencia de datos",
        "src/bayesian_tph_forecasting/pipelines/data_science/nodes.py",
        "Clustering geológico y ensamblado diario de variables.",
    ),
    (
        "Inferencia Bayesiana",
        "src/bayesian_tph_forecasting/pipelines/bayesian_inference/__init__.py",
        "Interfaz pública de la pipeline de inferencia Bayesiana.",
    ),
    (
        "Inferencia Bayesiana",
        "src/bayesian_tph_forecasting/pipelines/bayesian_inference/pipeline.py",
        "Declaración del backtesting y del ajuste final.",
    ),
    (
        "Inferencia Bayesiana",
        "src/bayesian_tph_forecasting/pipelines/bayesian_inference/nodes.py",
        "Modelo jerárquico, posterior predictivo y validación móvil.",
    ),
    (
        "Reporting",
        "src/bayesian_tph_forecasting/pipelines/reporting/__init__.py",
        "Interfaz pública de la pipeline de reporting.",
    ),
    (
        "Reporting",
        "src/bayesian_tph_forecasting/pipelines/reporting/pipeline.py",
        "Declaración de los productos que consumirá el blog.",
    ),
    (
        "Reporting",
        "src/bayesian_tph_forecasting/pipelines/reporting/nodes.py",
        "Bridge, aplicación interactiva y ficha del modelo.",
    ),
    (
        "Composición",
        "src/bayesian_tph_forecasting/pipeline_registry.py",
        "Registro que une las cuatro pipelines en el DAG global.",
    ),
    (
        "Pruebas",
        "tests/test_public_contracts.py",
        "Contratos públicos de identificadores, rendimiento y espacio.",
    ),
    (
        "Pruebas",
        "tests/test_reporting.py",
        "Identidad contable que debe cerrar el bridge.",
    ),
]


def collect_source_steps() -> list[dict[str, str]]:
    """
    Lee en orden pedagógico todos los archivos que forman el recorrido del proyecto.

    Parámetros:
    -------------
    No aplica.

    Retorna:
    ---------
    list[dict[str, str]] : metadatos y contenido textual de cada paso del explorador.
    """
    steps: list[dict[str, str]] = []
    for index, (section, relative_path, description) in enumerate(SOURCE_STEPS, start=1):
        source_path = PROJECT_ROOT / relative_path
        if not source_path.is_file():
            raise FileNotFoundError(f"No existe el archivo requerido por el explorador: {source_path}")
        steps.append(
            {
                "id": f"paso-{index:02d}",
                "section": section,
                "path": relative_path,
                "description": description,
                "language": source_path.suffix.lstrip(".") or "text",
                "source": source_path.read_text(encoding="utf-8"),
            }
        )
    return steps


def build_explorer_html(steps: list[dict[str, str]]) -> str:
    """
    Construye el documento HTML autocontenido del explorador de código.

    Parámetros:
    -------------
    steps : archivos ordenados con sus metadatos y contenido fuente.

    Retorna:
    ---------
    str : documento HTML listo para publicarse como recurso estático de Quarto.
    """
    payload = json.dumps(steps, ensure_ascii=False).replace("</", "<\\/")
    return rf"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Recorrido del código fuente</title>
  <style>
    :root{{--bg:#f7f9fb;--panel:#fff;--panel-2:#f1f4f7;--ink:#202830;--muted:#66717b;--line:#dfe5ea;--accent:#2c66c9;--code:#171c21;--code-ink:#e7edf3}}
    *{{box-sizing:border-box}} html,body{{height:100%}} body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}}
    button,input{{font:inherit}} .app{{display:grid;grid-template-columns:minmax(250px,320px) 1fr;height:100vh;overflow:hidden}}
    aside{{display:flex;min-width:0;min-height:0;height:100vh;flex-direction:column;overflow:hidden;border-right:1px solid var(--line);background:var(--panel)}}
    .brand{{padding:18px;border-bottom:1px solid var(--line)}} .eyebrow{{color:var(--accent);font-size:11px;font-weight:800;letter-spacing:.12em;text-transform:uppercase}}
    .back{{display:inline-flex;align-items:center;margin-bottom:12px;color:var(--accent);font-size:13px;font-weight:750;text-decoration:none}} .back:hover{{text-decoration:underline}}
    h1{{margin:5px 0 3px;font-size:20px}} .brand p{{margin:0;color:var(--muted);font-size:13px}}
    .search{{padding:12px;border-bottom:1px solid var(--line)}} .search input{{width:100%;padding:9px 11px;border:1px solid var(--line);border-radius:7px;background:var(--bg);color:var(--ink)}}
    nav{{min-height:0;height:0;flex:1 1 0;overflow-x:hidden;overflow-y:scroll;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;padding:8px;scrollbar-color:var(--muted) transparent;scrollbar-width:thin}} .step{{display:block;width:100%;margin:2px 0;padding:9px 10px;border:0;border-radius:7px;background:transparent;color:var(--ink);text-align:left;cursor:pointer}}
    .step:hover{{background:var(--panel-2)}} .step.active{{background:#e9f0fb;color:#174d9f}} .step small{{display:block;color:var(--muted);font-size:11px}}
    main{{display:flex;min-width:0;flex-direction:column;overflow:hidden}} header{{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;padding:18px 22px;border-bottom:1px solid var(--line);background:var(--panel)}}
    header h2{{margin:2px 0 3px;font:700 18px/1.3 ui-monospace,SFMono-Regular,Menlo,monospace;overflow-wrap:anywhere}} header p{{margin:0;color:var(--muted)}}
    .counter{{flex:0 0 auto;padding:5px 9px;border:1px solid var(--line);border-radius:999px;color:var(--muted);font-size:12px}}
    .code-wrap{{min-height:0;flex:1;overflow:auto;background:var(--code)}} pre{{min-width:max-content;margin:0;padding:22px}} code{{color:var(--code-ink);font:13px/1.65 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;tab-size:4}}
    .tok-comment{{color:#7f8c98;font-style:italic}} .tok-keyword{{color:#d88ce8}} .tok-builtin{{color:#76b7f2}} .tok-string{{color:#9fd58b}} .tok-number{{color:#e8b36d}} .tok-key{{color:#75b9e7}} .tok-heading{{color:#70c7c9;font-weight:750}} .tok-markup{{color:#d7a5d1}} .tok-operator{{color:#aebbc7}}
    footer{{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:11px 16px;border-top:1px solid var(--line);background:var(--panel)}}
    .actions{{display:flex;gap:8px}} footer button{{padding:7px 11px;border:1px solid var(--line);border-radius:7px;background:var(--panel);color:var(--ink);cursor:pointer}} footer button:hover:not(:disabled){{border-color:#a9bad0;color:var(--accent)}} footer button:disabled{{opacity:.4;cursor:not-allowed}}
    .hint{{color:var(--muted);font-size:12px}}
    html[data-theme="dark"]{{--bg:#272b30;--panel:#2f353b;--panel-2:#383f46;--ink:#eef1f4;--muted:#aeb7c0;--line:#454c54;--accent:#7aa7dd;--code:#171b1f;--code-ink:#e1e8ef}} html[data-theme="dark"] .step.active{{background:#35445a;color:#b5d2f5}}
    @media(prefers-color-scheme:dark){{html:not([data-theme]){{--bg:#272b30;--panel:#2f353b;--panel-2:#383f46;--ink:#eef1f4;--muted:#aeb7c0;--line:#454c54;--accent:#7aa7dd;--code:#171b1f;--code-ink:#e1e8ef}}html:not([data-theme]) .step.active{{background:#35445a;color:#b5d2f5}}}}
    @media(max-width:760px){{.app{{grid-template-columns:1fr;grid-template-rows:auto 1fr}} aside{{height:auto;border-right:0;border-bottom:1px solid var(--line)}} .brand{{padding:12px 14px}} .brand p{{display:none}} .search{{padding:8px 12px}} nav{{display:flex;min-height:auto;height:auto;flex:none;gap:5px;overflow-x:auto;overflow-y:hidden;padding:7px 10px}} .step{{flex:0 0 auto;width:auto;max-width:230px}} main{{min-height:0}} header{{padding:13px 15px}} header p,.hint{{display:none}} pre{{padding:16px}}}}
  </style>
</head>
<body>
<div class="app">
  <aside><div class="brand"><a class="back" href="../07-codigo-fuente.html" target="_top">← Volver al artículo</a><div class="eyebrow">Proyecto Kedro</div><h1>Recorrido del código</h1><p>De la configuración a las pruebas, en orden de lectura.</p></div><div class="search"><input id="search" type="search" placeholder="Buscar archivo o etapa…" aria-label="Buscar archivo o etapa"></div><nav id="steps" aria-label="Archivos del proyecto"></nav></aside>
  <main><header><div><div class="eyebrow" id="section"></div><h2 id="path"></h2><p id="description"></p></div><span class="counter" id="counter"></span></header><div class="code-wrap"><pre><code id="source"></code></pre></div><footer><span class="hint">Usa ← y → para avanzar</span><div class="actions"><button id="copy">Copiar</button><button id="previous">← Anterior</button><button id="next">Siguiente →</button></div></footer></main>
</div>
<script>
const FILES={payload};
function syncTheme(){{try{{document.documentElement.dataset.theme=parent.document.body.classList.contains('quarto-dark')?'dark':'light'}}catch{{}}}}syncTheme();try{{new MutationObserver(syncTheme).observe(parent.document.body,{{attributes:true,attributeFilter:['class']}})}}catch{{}}
const nav=document.getElementById('steps'),source=document.getElementById('source'),search=document.getElementById('search');let current=0;
nav.addEventListener('wheel',event=>{{if(Math.abs(event.deltaY)>Math.abs(event.deltaX)){{nav.scrollTop+=event.deltaY;event.preventDefault()}}}},{{passive:false}});
function escapeHtml(value){{return value.replace(/[&<>]/g,char=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[char]))}}
function decorate(value,pattern){{let output='',last=0,match;while((match=pattern.exec(value))!==null){{output+=escapeHtml(value.slice(last,match.index));const token=match[0],kind=Object.entries(match.groups||{{}}).find(([,content])=>content!==undefined)?.[0]||'operator';output+=`<span class="tok-${{kind}}">${{escapeHtml(token)}}</span>`;last=match.index+token.length;if(token.length===0)pattern.lastIndex++}}return output+escapeHtml(value.slice(last))}}
function highlightSource(value,language){{
  if(language==='py')return decorate(value,/(?<string>"{{3}}[\s\S]*?"{{3}}|'{{3}}[\s\S]*?'{{3}}|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|(?<comment>\#[^\n]*)|(?<keyword>\b(?:and|as|assert|async|await|break|case|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|match|nonlocal|not|or|pass|raise|return|try|while|with|yield)\b)|(?<builtin>\b(?:Any|True|False|None|bool|dict|float|int|list|set|str|tuple)\b)|(?<number>\b(?:0[xob][\da-fA-F]+|\d+(?:\.\d+)?)\b)/g);
  if(language==='md')return decorate(value,/(?<heading>^#{{1,6}}\s.*$)|(?<markup>^\s*(?:```|[-*+]\s|\d+\.\s).*$|`[^`]+`|\*{{1,2}}[^*]+\*{{1,2}}|\[[^\]]+\]\([^\)]+\))/gm);
  if(['yml','yaml','toml','sh','bash'].includes(language))return decorate(value,/(?<comment>\#[^\n]*)|(?<string>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|(?<key>^[ \t]*[A-Za-z_][\w.-]*(?=\s*[:=]))|(?<keyword>\b(?:true|false|null|yes|no|if|then|else|fi|for|in|do|done|case|esac|function|export)\b)|(?<number>\b\d+(?:\.\d+)?\b)/gmi);
  return escapeHtml(value)
}}
function visibleIndexes(){{const q=search.value.trim().toLowerCase();return FILES.map((f,i)=>[f,i]).filter(([f])=>!q||`${{f.section}} ${{f.path}} ${{f.description}}`.toLowerCase().includes(q)).map(([,i])=>i)}}
function renderNav(){{const visible=visibleIndexes();nav.innerHTML='';visible.forEach(i=>{{const f=FILES[i],button=document.createElement('button');button.className=`step${{i===current?' active':''}}`;button.innerHTML=`<small>${{String(i+1).padStart(2,'0')}} · ${{f.section}}</small>${{f.path}}`;button.onclick=()=>show(i);nav.appendChild(button)}})}}
function show(index){{current=Math.max(0,Math.min(FILES.length-1,index));const f=FILES[current];document.getElementById('section').textContent=f.section;document.getElementById('path').textContent=f.path;document.getElementById('description').textContent=f.description;document.getElementById('counter').textContent=`${{current+1}} / ${{FILES.length}}`;source.innerHTML=highlightSource(f.source,f.language);document.getElementById('previous').disabled=current===0;document.getElementById('next').disabled=current===FILES.length-1;history.replaceState(null,'',`#${{f.id}}`);renderNav();document.querySelector('.code-wrap').scrollTop=0;document.querySelector('.step.active')?.scrollIntoView({{block:'nearest',inline:'nearest'}})}}
search.oninput=renderNav;document.getElementById('previous').onclick=()=>show(current-1);document.getElementById('next').onclick=()=>show(current+1);document.getElementById('copy').onclick=async e=>{{await navigator.clipboard.writeText(FILES[current].source);const old=e.target.textContent;e.target.textContent='Copiado';setTimeout(()=>e.target.textContent=old,1200)}};
document.addEventListener('keydown',e=>{{if(e.target===search)return;if(e.key==='ArrowLeft')show(current-1);if(e.key==='ArrowRight')show(current+1)}});const initial=FILES.findIndex(f=>`#${{f.id}}`===location.hash);show(initial>=0?initial:0);
</script>
</body>
</html>"""


def main() -> None:
    """
    Genera el explorador en la carpeta de recursos publicables del proyecto.

    Parámetros:
    -------------
    No aplica.

    Retorna:
    ---------
    None. La función escribe el documento HTML en ``source/index.html``.
    """
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(build_explorer_html(collect_source_steps()), encoding="utf-8")
    print(f"source-explorer: {len(SOURCE_STEPS)} archivos ordenados")


if __name__ == "__main__":
    main()
