(function () {
  "use strict";

  const ROOT_ID = "lane-cutoff-lab";
  const PLOTLY_URL = "https://cdn.plot.ly/plotly-3.6.0.min.js";
  const COLORS = {
    blue: "#3976a8",
    green: "#2b8a66",
    red: "#bd2a2a",
    gold: "#d5a02c",
    ink: "#26323d",
    gray: "#7b858e",
    lightGray: "#c8ced4",
    stock1: "#d5a02c",
    stock2: "#9a6fb0",
    dump1: "#7b858e",
    dump2: "#aeb5bb",
    overflow: "#bd2a2a",
  };

  const DEFAULTS = {
    "lane-resource": 240,
    "lane-mean-grade": 0.62,
    "lane-grade-cv": 0.65,
    "lane-main-price": 6800,
    "lane-main-recovery": 88,
    "lane-mining-cost": 2.5,
    "lane-processing-cost": 9,
    "lane-fixed-cost": 80,
    "lane-opportunity-cost": 120,
    "lane-mine-capacity": 45,
    "lane-plant-capacity": 20,
    "lane-refinery-capacity": 150,
    "lane-dump-count": "1",
    "lane-stock-count": "1",
    "lane-dump-1-cost": 1.5,
    "lane-dump-1-capacity": 170,
    "lane-dump-2-cost": 3,
    "lane-dump-2-capacity": 80,
    "lane-stock-1-cost": 1.25,
    "lane-stock-1-capacity": 25,
    "lane-stock-1-factor": 0.65,
    "lane-stock-2-cost": 2,
    "lane-stock-2-capacity": 20,
    "lane-stock-2-factor": 0.5,
    "lane-product-count": "1",
    "lane-product-1-type": "byproduct",
    "lane-product-1-price": 32000,
    "lane-product-1-recovery": 65,
    "lane-product-1-ratio": 0.006,
    "lane-product-1-capacity": 12,
    "lane-product-2-type": "coproduct",
    "lane-product-2-price": 18000,
    "lane-product-2-recovery": 55,
    "lane-product-2-ratio": 0.012,
    "lane-product-2-capacity": 18,
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function numberValue(id) {
    const value = Number.parseFloat(byId(id).value);
    return Number.isFinite(value) ? value : 0;
  }

  function normalPdf(x, mean, sigma) {
    const z = (x - mean) / sigma;
    return Math.exp(-0.5 * z * z) / (sigma * Math.sqrt(2 * Math.PI));
  }

  function buildInventory(params) {
    const n = 180;
    const mean = Math.max(params.meanGrade, 0.0001);
    const cv = Math.max(params.gradeCv, 0.05);
    const sigma = Math.sqrt(Math.log(1 + cv * cv));
    const mu = Math.log(mean) - 0.5 * sigma * sigma;
    const minGrade = Math.max(mean * 0.025, 0.00001);
    const maxGrade = Math.max(mean * 5.5, 0.02);
    const step = (maxGrade - minGrade) / (n - 1);
    const bins = [];
    let weightSum = 0;

    for (let i = 0; i < n; i += 1) {
      const grade = minGrade + i * step;
      const weight = normalPdf(Math.log(grade), mu, sigma) / grade;
      bins.push({ grade, weight });
      weightSum += weight;
    }

    return bins.map((bin) => ({
      grade: bin.grade,
      tonnes: (params.resourceTonnes * bin.weight) / weightSum,
    }));
  }

  function readParams() {
    const dumpCount = Number.parseInt(byId("lane-dump-count").value, 10);
    const stockCount = Number.parseInt(byId("lane-stock-count").value, 10);
    const productCount = Number.parseInt(byId("lane-product-count").value, 10);
    const dumps = [];
    const stocks = [];
    const products = [];

    for (let i = 1; i <= dumpCount; i += 1) {
      dumps.push({
        name: `Botadero ${i}`,
        cost: numberValue(`lane-dump-${i}-cost`),
        capacity: numberValue(`lane-dump-${i}-capacity`) * 1e6,
      });
    }

    for (let i = 1; i <= stockCount; i += 1) {
      stocks.push({
        name: `Stockpile ${i}`,
        cost: numberValue(`lane-stock-${i}-cost`),
        capacity: numberValue(`lane-stock-${i}-capacity`) * 1e6,
        factor: numberValue(`lane-stock-${i}-factor`),
      });
    }

    for (let i = 1; i <= productCount; i += 1) {
      products.push({
        name: `Producto ${i}`,
        type: byId(`lane-product-${i}-type`).value,
        price: numberValue(`lane-product-${i}-price`),
        recovery: numberValue(`lane-product-${i}-recovery`) / 100,
        ratio: numberValue(`lane-product-${i}-ratio`),
        capacity: numberValue(`lane-product-${i}-capacity`) * 1e3,
      });
    }

    return {
      resourceTonnes: numberValue("lane-resource") * 1e6,
      meanGrade: numberValue("lane-mean-grade") / 100,
      gradeCv: numberValue("lane-grade-cv"),
      mainPrice: numberValue("lane-main-price"),
      mainRecovery: numberValue("lane-main-recovery") / 100,
      miningCost: numberValue("lane-mining-cost"),
      processingCost: numberValue("lane-processing-cost"),
      fixedAnnual: numberValue("lane-fixed-cost") * 1e6,
      opportunityAnnual: numberValue("lane-opportunity-cost") * 1e6,
      mineCapacity: numberValue("lane-mine-capacity") * 1e6,
      plantCapacity: numberValue("lane-plant-capacity") * 1e6,
      refineryCapacity: numberValue("lane-refinery-capacity") * 1e3,
      dumps,
      stocks,
      products,
    };
  }

  function marginalRevenuePerGrade(params) {
    return params.products.reduce(
      (total, product) =>
        total + product.price * product.recovery * product.ratio,
      params.mainPrice * params.mainRecovery,
    );
  }

  function allocateSubMarginal(bins, cutoff, params, revenueSlope) {
    const below = bins
      .filter((bin) => bin.grade < cutoff)
      .map((bin) => ({ grade: bin.grade, tonnes: bin.tonnes }))
      .sort((a, b) => b.grade - a.grade);
    const allocations = {};
    let stockOption = 0;
    let dumpCost = 0;
    let overflow = 0;

    params.stocks.forEach((stock) => {
      allocations[stock.name] = 0;
      let remainingCapacity = stock.capacity;

      below.forEach((bin) => {
        if (remainingCapacity <= 0 || bin.tonnes <= 0) return;
        const optionPerTonne =
          stock.factor * (revenueSlope * bin.grade - params.processingCost) -
          stock.cost;
        if (optionPerTonne <= 0) return;
        const assigned = Math.min(bin.tonnes, remainingCapacity);
        bin.tonnes -= assigned;
        remainingCapacity -= assigned;
        allocations[stock.name] += assigned;
        stockOption += assigned * optionPerTonne;
      });
    });

    const residual = below.reduce((sum, bin) => sum + bin.tonnes, 0);
    let tonnesToAllocate = residual;
    const orderedDumps = [...params.dumps].sort((a, b) => a.cost - b.cost);

    orderedDumps.forEach((dump) => {
      const assigned = Math.min(tonnesToAllocate, dump.capacity);
      allocations[dump.name] = assigned;
      dumpCost += assigned * dump.cost;
      tonnesToAllocate -= assigned;
    });

    if (tonnesToAllocate > 0) {
      const highestDumpCost = orderedDumps.length
        ? Math.max(...orderedDumps.map((dump) => dump.cost))
        : 0;
      overflow = tonnesToAllocate;
      allocations["Destino excedente"] = overflow;
      dumpCost += overflow * (highestDumpCost + 25);
    }

    return { allocations, stockOption, dumpCost, overflow };
  }

  function evaluateCutoff(cutoff, bins, params) {
    const revenueSlope = marginalRevenuePerGrade(params);
    const processedBins = bins.filter((bin) => bin.grade >= cutoff);
    const processedTonnes = processedBins.reduce(
      (sum, bin) => sum + bin.tonnes,
      0,
    );
    const gradeTonnes = processedBins.reduce(
      (sum, bin) => sum + bin.tonnes * bin.grade,
      0,
    );
    const mainMetal = gradeTonnes * params.mainRecovery;
    let revenue = mainMetal * params.mainPrice;
    const productOutputs = [];

    params.products.forEach((product) => {
      const output = gradeTonnes * product.ratio * product.recovery;
      productOutputs.push({ ...product, output });
      revenue += output * product.price;
    });

    const destinations = allocateSubMarginal(
      bins,
      cutoff,
      params,
      revenueSlope,
    );
    const timeTerms = [
      { name: "Mina", years: params.resourceTonnes / params.mineCapacity },
      { name: "Planta", years: processedTonnes / params.plantCapacity },
      { name: "Refinería Cu", years: mainMetal / params.refineryCapacity },
    ];

    productOutputs
      .filter((product) => product.type === "coproduct")
      .forEach((product) => {
        timeTerms.push({
          name: `Mercado ${product.name}`,
          years: product.output / product.capacity,
        });
      });

    const active = timeTerms.reduce((best, term) =>
      term.years > best.years ? term : best,
    );
    const annualTimeCost = params.fixedAnnual + params.opportunityAnnual;
    const operatingCost =
      params.resourceTonnes * params.miningCost +
      processedTonnes * params.processingCost +
      destinations.dumpCost;
    const value =
      revenue -
      operatingCost -
      annualTimeCost * active.years +
      destinations.stockOption;

    return {
      cutoff,
      value,
      duration: active.years,
      bottleneck: active.name,
      processedTonnes,
      mainMetal,
      destinations: destinations.allocations,
      overflow: destinations.overflow,
      timeTerms,
    };
  }

  function economicReferences(params) {
    const a = marginalRevenuePerGrade(params);
    const marginalDump = params.dumps.length
      ? Math.min(...params.dumps.map((dump) => dump.cost))
      : 0;
    const variable = params.miningCost + params.processingCost - marginalDump;
    const annual = params.fixedAnnual + params.opportunityAnnual;
    const gm = variable / a;
    const gc = (variable + annual / params.plantCapacity) / a;
    const denominator =
      a - (annual * params.mainRecovery) / params.refineryCapacity;
    const gr = denominator > 0 ? variable / denominator : Number.NaN;
    return { gm, gc, gr };
  }

  function solveScenario(params) {
    const bins = buildInventory(params);
    const maxGrade = bins[bins.length - 1].grade * 0.82;
    const minGrade = bins[0].grade;
    const n = 120;
    const results = [];

    for (let i = 0; i < n; i += 1) {
      const cutoff = minGrade + (i / (n - 1)) * (maxGrade - minGrade);
      results.push(evaluateCutoff(cutoff, bins, params));
    }

    const optimum = results.reduce((best, result) =>
      result.value > best.value ? result : best,
    );
    return {
      results,
      optimum,
      references: economicReferences(params),
    };
  }

  function formatGrade(value) {
    return `${(100 * value).toFixed(2)} %`;
  }

  function formatValue(value) {
    return `${(value / 1e6).toLocaleString("es-CL", {
      maximumFractionDigits: 0,
    })} MUSD`;
  }

  function commonLayout(title) {
    const rootStyles = window.getComputedStyle(byId(ROOT_ID));
    const plotText =
      rootStyles.getPropertyValue("--lane-plot-text").trim() || COLORS.ink;
    const plotGrid =
      rootStyles.getPropertyValue("--lane-plot-grid").trim() ||
      "rgba(100,110,120,0.18)";
    const plotSurface =
      rootStyles.getPropertyValue("--lane-plot-surface").trim() ||
      "rgba(0,0,0,0)";

    return {
      title: {
        text: `<b>${title}</b>`,
        x: 0.02,
        xanchor: "left",
        y: 0.98,
        yanchor: "top",
        font: { size: 17 },
      },
      font: {
        family: "Calibri, Carlito, Arial, sans-serif",
        color: plotText,
        size: 12,
      },
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: plotSurface,
      margin: { l: 60, r: 52, t: 92, b: 56 },
      hovermode: "closest",
      legend: {
        orientation: "h",
        x: 0.5,
        xanchor: "center",
        y: 0.9,
        yanchor: "top",
      },
      _laneGridColor: plotGrid,
      _laneTextColor: plotText,
    };
  }

  function renderObjective(solution) {
    const cutoffs = solution.results.map((result) => result.cutoff * 100);
    const values = solution.results.map((result) => result.value / 1e6);
    const durations = solution.results.map((result) => result.duration);
    const layout = commonLayout(
      "Valor y duración del escenario según ley de corte",
    );
    const gridColor = layout._laneGridColor;
    const textColor = layout._laneTextColor;
    delete layout._laneGridColor;
    delete layout._laneTextColor;
    layout.xaxis = {
      title: "Ley de corte (% metal principal)",
      gridcolor: gridColor,
    };
    layout.yaxis = {
      title: "Valor del escenario (MUSD)",
      gridcolor: gridColor,
    };
    layout.yaxis2 = {
      title: "Duración (años)",
      overlaying: "y",
      side: "right",
      showgrid: false,
    };
    layout.margin.t = 130;
    layout.legend = {
      orientation: "h",
      x: 0.5,
      xanchor: "center",
      y: 1.03,
      yanchor: "bottom",
    };
    layout.shapes = [
      {
        type: "line",
        x0: solution.optimum.cutoff * 100,
        x1: solution.optimum.cutoff * 100,
        y0: 0,
        y1: 1,
        yref: "paper",
        line: { color: COLORS.ink, width: 1.5, dash: "dash" },
      },
    ];
    layout.annotations = [
      {
        x: solution.optimum.cutoff * 100,
        y: 1,
        yref: "paper",
        text: `Óptimo: ${formatGrade(solution.optimum.cutoff)}`,
        showarrow: false,
        yshift: 11,
        font: { size: 11, color: textColor },
      },
    ];

    Plotly.react(
      "lane-objective-chart",
      [
        {
          x: cutoffs,
          y: values,
          type: "scatter",
          mode: "lines",
          name: "Valor económico",
          line: { color: COLORS.blue, width: 3 },
          hovertemplate: "Ley %{x:.2f}%<br>Valor %{y:.0f} MUSD<extra></extra>",
        },
        {
          x: cutoffs,
          y: durations,
          type: "scatter",
          mode: "lines",
          name: "Duración",
          yaxis: "y2",
          line: { color: COLORS.red, width: 2, dash: "dot" },
          hovertemplate: "Ley %{x:.2f}%<br>Duración %{y:.2f} años<extra></extra>",
        },
      ],
      layout,
      { responsive: true, displaylogo: false },
    );
  }

  function renderCutoffs(solution) {
    const refs = solution.references;
    const labels = ["Lane: mina", "Lane: planta", "Lane: refinería", "Óptimo"];
    const values = [
      refs.gm * 100,
      refs.gc * 100,
      Number.isFinite(refs.gr) ? refs.gr * 100 : 0,
      solution.optimum.cutoff * 100,
    ];
    const validText = values.map((value, index) =>
      index === 2 && !Number.isFinite(refs.gr)
        ? "No factible"
        : `${value.toFixed(2)} %`,
    );
    const layout = commonLayout("Leyes económicas y óptimo numérico");
    const gridColor = layout._laneGridColor;
    delete layout._laneGridColor;
    delete layout._laneTextColor;
    layout.margin = { l: 112, r: 30, t: 76, b: 52 };
    layout.xaxis = {
      title: "Ley (% metal principal)",
      gridcolor: gridColor,
      rangemode: "tozero",
    };
    layout.yaxis = { automargin: true };
    layout.showlegend = false;

    Plotly.react(
      "lane-cutoffs-chart",
      [
        {
          x: values,
          y: labels,
          type: "bar",
          orientation: "h",
          marker: {
            color: [COLORS.gray, COLORS.gold, COLORS.red, COLORS.blue],
          },
          text: validText,
          textposition: "outside",
          cliponaxis: false,
          hovertemplate: "%{y}: %{text}<extra></extra>",
        },
      ],
      layout,
      { responsive: true, displaylogo: false },
    );
  }

  function renderDestinations(solution) {
    const optimum = solution.optimum;
    const destinationNames = ["Planta", ...Object.keys(optimum.destinations)];
    const destinationValues = [
      optimum.processedTonnes / 1e6,
      ...Object.values(optimum.destinations).map((value) => value / 1e6),
    ];
    const colorMap = {
      Planta: COLORS.green,
      "Stockpile 1": COLORS.stock1,
      "Stockpile 2": COLORS.stock2,
      "Botadero 1": COLORS.dump1,
      "Botadero 2": COLORS.dump2,
      "Destino excedente": COLORS.overflow,
    };
    const layout = commonLayout("Balance de masa en la política óptima");
    const gridColor = layout._laneGridColor;
    delete layout._laneGridColor;
    delete layout._laneTextColor;
    layout.margin = { l: 46, r: 25, t: 76, b: 92 };
    layout.xaxis = { tickangle: -25, automargin: true };
    layout.yaxis = {
      title: "Tonelaje (Mt)",
      gridcolor: gridColor,
    };
    layout.showlegend = false;

    Plotly.react(
      "lane-destinations-chart",
      [
        {
          x: destinationNames,
          y: destinationValues,
          type: "bar",
          marker: {
            color: destinationNames.map(
              (name) => colorMap[name] || COLORS.lightGray,
            ),
          },
          text: destinationValues.map((value) => value.toFixed(1)),
          textposition: "outside",
          cliponaxis: false,
          hovertemplate: "%{x}: %{y:.2f} Mt<extra></extra>",
        },
      ],
      layout,
      { responsive: true, displaylogo: false },
    );
  }

  function updateKpis(solution) {
    const optimum = solution.optimum;
    byId("lane-kpi-cutoff").textContent = formatGrade(optimum.cutoff);
    byId("lane-kpi-bottleneck").textContent = optimum.bottleneck;
    byId("lane-kpi-value").textContent = formatValue(optimum.value);
    byId("lane-kpi-duration").textContent =
      `${optimum.duration.toFixed(2)} años`;

    const timeDetail = optimum.timeTerms
      .map((term) => `${term.name}: ${term.years.toFixed(2)} años`)
      .join(" · ");
    const warning =
      optimum.overflow > 1
        ? ` Advertencia: ${(optimum.overflow / 1e6).toFixed(1)} Mt exceden la capacidad declarada de disposición y reciben una penalización económica.`
        : "";
    byId("lane-lab-status").textContent =
      `Tiempos equivalentes en el óptimo: ${timeDetail}.${warning}`;
    byId("lane-lab-status").classList.toggle(
      "is-warning",
      optimum.overflow > 1,
    );
  }

  function updateVisibility() {
    const dumpCount = Number.parseInt(byId("lane-dump-count").value, 10);
    const stockCount = Number.parseInt(byId("lane-stock-count").value, 10);
    const productCount = Number.parseInt(byId("lane-product-count").value, 10);

    byId("lane-dump-2").hidden = dumpCount < 2;
    byId("lane-stock-1").hidden = stockCount < 1;
    byId("lane-stock-2").hidden = stockCount < 2;
    byId("lane-product-1").hidden = productCount < 1;
    byId("lane-product-2").hidden = productCount < 2;

    for (let i = 1; i <= 2; i += 1) {
      const product = byId(`lane-product-${i}`);
      const marketField = product.querySelector(".lane-market-field");
      marketField.hidden = byId(`lane-product-${i}-type`).value !== "coproduct";
    }
  }

  function render() {
    updateVisibility();
    const solution = solveScenario(readParams());
    updateKpis(solution);
    renderObjective(solution);
    renderCutoffs(solution);
    renderDestinations(solution);
  }

  function reset() {
    Object.entries(DEFAULTS).forEach(([id, value]) => {
      byId(id).value = value;
    });
    render();
  }

  function loadPlotly() {
    if (window.Plotly) return Promise.resolve();
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = PLOTLY_URL;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  function initialize() {
    const root = byId(ROOT_ID);
    if (!root) return;

    loadPlotly()
      .then(() => {
        let timer;
        root.addEventListener("input", () => {
          window.clearTimeout(timer);
          timer = window.setTimeout(render, 80);
        });
        root.addEventListener("change", render);
        byId("lane-lab-reset").addEventListener("click", reset);

        const themeObserver = new MutationObserver((mutations) => {
          if (mutations.some((mutation) => mutation.attributeName === "class")) {
            window.requestAnimationFrame(render);
          }
        });
        themeObserver.observe(document.body, { attributes: true });

        render();
      })
      .catch(() => {
        byId("lane-lab-status").textContent =
          "No fue posible cargar Plotly. Verifica la conexión y recarga la página.";
        byId("lane-lab-status").classList.add("is-warning");
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize);
  } else {
    initialize();
  }
})();
