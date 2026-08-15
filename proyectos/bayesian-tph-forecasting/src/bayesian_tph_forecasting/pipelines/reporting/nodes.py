"""
Construye el bridge chart, la aplicación HTML autocontenida y la ficha técnica del modelo.
"""

from __future__ import annotations

import json
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BRIDGE_COMPONENTS = [
    ("Base contextual", "base_component", "base", "total"),
    ("Firma geológica", "contrib_geology", "mine", "delta"),
    ("Procedencia", "contrib_source", "mine", "delta"),
    ("Dureza", "contrib_hardness", "mine", "delta"),
    ("Granulometría", "contrib_granulometry", "plant", "delta"),
    ("Circuito aguas arriba", "contrib_upstream", "plant", "delta"),
    ("Cubas en rango", "contrib_sumps", "plant", "delta"),
    ("Chancado auxiliar", "contrib_auxiliary_crushing", "plant", "delta"),
    ("Molienda secundaria", "contrib_secondary", "plant", "delta"),
    ("Esperado por contexto", "y_pred_mean", "model", "total"),
    ("Operación no explicada", "residual_actual_minus_model", "operation", "delta"),
    ("Observado", "y_true", "actual", "total"),
]


def _add_reporting_families(backtest_predictions: pd.DataFrame) -> pd.DataFrame:
    """
    Agrupa contribuciones atómicas del modelo en familias legibles para reporting.

    Parámetros:
    -------------
    backtest_predictions : predicciones diarias con contribuciones por variable.

    Retorna:
    ---------
    pd.DataFrame : copia enriquecida con las familias usadas por el bridge.
    """
    df = backtest_predictions.copy()
    df["contrib_hardness"] = df["contrib__penetration_rate_mean"] + df["contrib_hardness_mix"]
    df["contrib_granulometry"] = (
        df["contrib__feed_fines_pct_mean"] + df["contrib__feed_fines_pct_centered_sq"]
    )
    df["contrib_upstream"] = df["contrib__upstream_available_pct"]
    df["contrib_sumps"] = df["contrib__discharge_sumps_in_range_pct"]
    df["contrib_auxiliary_crushing"] = df["contrib__auxiliary_crushing_available_pct"]
    df["contrib_secondary"] = df["contrib__secondary_grinding_available_pct"]
    return df


def build_bridge_summary(
    backtest_predictions: pd.DataFrame,
    reporting: dict,
) -> pd.DataFrame:
    """
    Materializa bridges mensuales y total respetando la identidad observado igual a modelo más residuo.

    Parámetros:
    -------------
    backtest_predictions : predicciones diarias fuera de muestra y sus contribuciones.
    reporting : configuración de presentación del producto de reporting.

    Retorna:
    ---------
    pd.DataFrame : componentes ordenados del bridge para cada mes y para el período completo.
    """
    df = _add_reporting_families(backtest_predictions)
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").astype(str)
    periods: list[tuple[str, pd.DataFrame]] = [("TOTAL", df)]
    periods.extend((month, group) for month, group in df.groupby("month", sort=True))

    rows: list[dict[str, Any]] = []
    for period, group in periods:
        for order, (label, column, family, kind) in enumerate(BRIDGE_COMPONENTS):
            rows.append(
                {
                    "period": period,
                    "order": order,
                    "label": label,
                    "column": column,
                    "family": family,
                    "kind": kind,
                    "value_tph": float(group[column].mean()),
                    "n_days": int(group["date"].nunique()),
                }
            )
    return pd.DataFrame(rows)


def _waterfall_geometry(bridge: pd.DataFrame) -> tuple[list[float], list[float], list[float]]:
    """
    Calcula bases, alturas y extremos acumulados para dibujar un gráfico de cascada.

    Parámetros:
    -------------
    bridge : componentes ordenados de un único período del bridge.

    Retorna:
    ---------
    tuple[list[float], list[float], list[float]] : bases, alturas y extremos de las barras.
    """
    running = 0.0
    bottoms: list[float] = []
    heights: list[float] = []
    endpoints: list[float] = []
    for row in bridge.itertuples(index=False):
        value = float(row.value_tph)
        if row.kind == "total":
            bottoms.append(0.0)
            heights.append(value)
            running = value
        else:
            bottoms.append(min(running, running + value))
            heights.append(abs(value))
            running += value
        endpoints.append(running)
    return bottoms, heights, endpoints


def plot_bridge_chart(bridge_summary: pd.DataFrame, reporting: dict):
    """
    Genera la vista estática principal del bridge para el período completo.

    Parámetros:
    -------------
    bridge_summary : componentes mensuales y totales producidos para reporting.
    reporting : configuración que contiene el título del gráfico.

    Retorna:
    ---------
    matplotlib.figure.Figure : figura estática del gráfico de cascada.
    """
    bridge = bridge_summary.loc[bridge_summary["period"].eq("TOTAL")].sort_values("order")
    bottoms, heights, endpoints = _waterfall_geometry(bridge)
    colors = {
        "base": "#315B66",
        "mine": "#C69C3C",
        "plant": "#2B8C87",
        "model": "#55717A",
        "operation": "#C44E52",
        "actual": "#202124",
    }
    x = np.arange(len(bridge))
    fig, ax = plt.subplots(figsize=(16, 7))
    bars = ax.bar(
        x,
        heights,
        bottom=bottoms,
        color=[colors[family] for family in bridge["family"]],
        edgecolor="white",
        linewidth=0.8,
        width=0.76,
    )
    endpoint_min, endpoint_max = min(endpoints), max(endpoints)
    local_span = max(100.0, endpoint_max - endpoint_min)
    offset = max(8.0, local_span * 0.045)
    for bar, endpoint, row in zip(bars, endpoints, bridge.itertuples(index=False), strict=True):
        label = f"{row.value_tph:+,.0f}" if row.kind == "delta" else f"{row.value_tph:,.0f}"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            endpoint + offset,
            label,
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )
    ax.set_xticks(x)
    ax.set_xticklabels(bridge["label"], rotation=28, ha="right")
    ax.set_ylabel("Rendimiento promedio (tph)")
    ax.set_ylim(endpoint_min - 0.20 * local_span, endpoint_max + 0.28 * local_span)
    fig.suptitle(reporting["title"], x=0.065, y=0.98, ha="left", fontsize=17, fontweight="bold")
    fig.text(
        0.065,
        0.93,
        "Caso ex post · ventana móvil de 12 meses · valores medios del período evaluado",
        color="#5F6B72",
        fontsize=10,
    )
    ax.grid(axis="y", linestyle="--", alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    return fig


def build_bridge_app(bridge_summary: pd.DataFrame, backtest_summary: pd.DataFrame) -> str:
    """
    Construye una aplicación estática con selector mensual, unidades y métricas del backtesting.

    Parámetros:
    -------------
    bridge_summary : componentes del bridge para todos los períodos disponibles.
    backtest_summary : métricas agregadas de validación fuera de muestra.

    Retorna:
    ---------
    str : documento HTML autocontenido en datos para renderizar la aplicación.
    """
    bridge_records = bridge_summary.to_dict(orient="records")
    metrics = backtest_summary.iloc[0].to_dict()
    payload = json.dumps({"bridge": bridge_records, "metrics": metrics}, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Bridge contextual de rendimiento</title>
  <script src="https://cdn.plot.ly/plotly-3.1.0.min.js"></script>
  <style>
    :root{{--ink:#183038;--muted:#65747a;--teal:#2b8c87;--gold:#c69c3c;--red:#c44e52;--panel:#f7f9f8}}
    *{{box-sizing:border-box}} body{{margin:0;font-family:Inter,system-ui,sans-serif;color:var(--ink);background:#fff}}
    main{{max-width:1240px;margin:auto;padding:24px}} header{{display:flex;gap:20px;justify-content:space-between;align-items:flex-end;flex-wrap:wrap}}
    h1{{margin:0;font-size:clamp(24px,3vw,40px)}} p{{color:var(--muted)}} .controls{{display:flex;gap:12px;flex-wrap:wrap}}
    label{{font-size:13px;font-weight:700}} select{{display:block;margin-top:5px;padding:9px 32px 9px 10px;border:1px solid #cad4d3;border-radius:7px;background:white}}
    .metrics{{display:grid;grid-template-columns:repeat(5,minmax(130px,1fr));gap:10px;margin:22px 0}}
    .metric{{background:var(--panel);border:1px solid #e1e8e6;border-radius:10px;padding:14px}} .metric small{{display:block;color:var(--muted)}} .metric b{{font-size:22px}}
    #chart{{height:620px}} .note{{border-left:4px solid var(--teal);padding:10px 14px;background:var(--panel)}}
    @media(max-width:760px){{.metrics{{grid-template-columns:repeat(2,1fr)}}#chart{{height:520px}}}}
  </style>
</head>
<body><main>
  <header><div><p>MODELO BAYESIANO JERÁRQUICO</p><h1>Bridge contextual de rendimiento</h1></div>
    <div class="controls"><label>Período<select id="period"></select></label><label>Unidad<select id="unit"><option value="tph">tph</option><option value="tpd">tpd</option></select></label></div>
  </header>
  <section class="metrics" id="metrics"></section><div id="chart"></div>
  <p class="note"><b>Lectura:</b> el residuo “Operación no explicada” cierra exactamente la identidad entre el rendimiento esperado por contexto y el observado. No representa causalidad automática.</p>
</main><script>
const DATA={payload};
const labels={{rmse:'RMSE',mae:'MAE',bias_pred_minus_actual:'Bias',mean_interval_90_coverage_pct:'Cobertura media',predictive_interval_90_coverage_pct:'Cobertura predictiva'}};
document.getElementById('metrics').innerHTML=Object.entries(labels).map(([k,v])=>`<div class="metric"><small>${{v}}</small><b>${{Number(DATA.metrics[k]).toFixed(1)}}</b></div>`).join('');
const periods=[...new Set(DATA.bridge.map(d=>d.period))]; const period=document.getElementById('period');
periods.forEach(p=>period.add(new Option(p==='TOTAL'?'Período completo':p,p)));
function draw(){{const p=period.value||'TOTAL',unit=document.getElementById('unit').value,m=unit==='tpd'?24:1,d=DATA.bridge.filter(x=>x.period===p).sort((a,b)=>a.order-b.order);
 const measure=d.map(x=>x.kind==='total'?'absolute':'relative');
 Plotly.react('chart',[{{type:'waterfall',orientation:'v',measure,x:d.map(x=>x.label),y:d.map(x=>x.value_tph*m),text:d.map(x=>`${{x.kind==='delta'&&x.value_tph>=0?'+':''}}${{(x.value_tph*m).toFixed(0)}}`),textposition:'outside',connector:{{line:{{color:'#9aabaa'}}}},increasing:{{marker:{{color:'#2b8c87'}}}},decreasing:{{marker:{{color:'#c44e52'}}}},totals:{{marker:{{color:'#315b66'}}}}}}],{{margin:{{t:55,r:25,b:120,l:75}},title:{{text:`${{p==='TOTAL'?'Período completo':p}} · ${{d[0].n_days}} días`,x:.02}},yaxis:{{title:unit,gridcolor:'#e7ecea'}},xaxis:{{tickangle:-25}},plot_bgcolor:'#fff',paper_bgcolor:'#fff',showlegend:false}},{{responsive:true,displaylogo:false}});}}
period.onchange=draw;document.getElementById('unit').onchange=draw;draw();
</script></body></html>"""


def build_model_card(
    backtest_summary: pd.DataFrame,
    model_input_schema: dict,
    reporting: dict,
) -> dict[str, Any]:
    """
    Resume propósito, límites, contrato de datos y métricas del modelo.

    Parámetros:
    -------------
    backtest_summary : métricas agregadas del backtesting.
    model_input_schema : contrato publicado de la matriz modelable.
    reporting : configuración de los intervalos y productos de reporting.

    Retorna:
    ---------
    dict[str, Any] : ficha técnica serializable del modelo y su validación.
    """
    metrics = {
        key: float(value)
        if isinstance(value, (np.floating, float))
        else int(value)
        if isinstance(value, (np.integer, int))
        else value
        for key, value in backtest_summary.iloc[0].to_dict().items()
    }
    return {
        "model_name": "bayesian_tph_forecasting",
        "intended_use": "Explicación ex post de desviaciones contextuales de rendimiento.",
        "not_intended_for": [
            "atribución causal automática",
            "pronóstico ex ante sin covariables de plan",
            "control directo de equipos",
        ],
        "validation_policy": "rolling 12 months, two-month horizon",
        "uncertainty": {
            "credible_mean_interval": "incertidumbre de la media contextual",
            "posterior_predictive_interval": "incertidumbre de una observación diaria",
            "probability": reporting["credible_probability"],
        },
        "data_contract": model_input_schema,
        "metrics": metrics,
    }
