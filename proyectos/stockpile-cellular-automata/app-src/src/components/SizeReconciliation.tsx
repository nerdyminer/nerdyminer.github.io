/**
 * Reconciliacion granulometrica por linea de molienda.
 *
 * Una curva por linea, en escala logaritmica de tamano, que es como se lee una
 * granulometria: el rango util abarca casi tres decadas y en escala lineal el
 * extremo fino queda aplastado contra el eje.
 *
 * Cada panel muestra la curva medida por la camara de descarga de esa linea,
 * la de alimentacion como referencia, y el P80 simulado marcado sobre
 * el 80 % de pasante. Las tres bandas de fondo son las clases de la operacion:
 * fino bajo 1 pulgada, intermedio entre 1 y 4, grueso sobre 4.
 *
 * Que se puede validar y que no
 * -----------------------------
 * El automata propaga UN tamano caracteristico por celda, de modo que produce
 * P80 y nada mas: la curva es enteramente medicion y el unico punto simulado es
 * el marcador del 80 %. Ademas las tres camaras no estan calibradas entre si
 * -- las de descarga leen unas 0.8 pulgadas mas fino que la de alimentacion --
 * asi que el nivel absoluto no es comparable y la diferencia entre lineas si.
 */

import { DECILES } from "../frames";
import type { LoadedRange, ReconciliationSeries } from "../frames";
import { formatSigned } from "../theme";
import type { SizeUnit } from "../units";
import { formatSize, formatTick, toUnit, unitSuffix } from "../units";
import { decadeTicks, logScale, linearScale } from "./chartAxes";

const WIDTH = 520;
const HEIGHT = 300;
const MARGINS = { top: 16, right: 18, bottom: 40, left: 46 };

const COLOUR_LINE1 = "#007ED3";
const COLOUR_LINE2 = "#E97132";
const COLOUR_FEED = "#8a9296";
const COLOUR_SIMULATED = "#1C434B";

/** Limites de clase de las camaras Split, en pulgadas. */
const FINE_CUT_IN = 1;
const COARSE_CUT_IN = 4;

/** Extremos del eje de tamano en pulgadas, fijos para que ambos paneles sean comparables. */
const SIZE_DOMAIN_IN: readonly [number, number] = [0.05, 20];

const ZONES = [
  { from: SIZE_DOMAIN_IN[0], to: FINE_CUT_IN, label: "fino", fill: "#eef4f6" },
  { from: FINE_CUT_IN, to: COARSE_CUT_IN, label: "intermedio", fill: "#fbf6e8" },
  { from: COARSE_CUT_IN, to: SIZE_DOMAIN_IN[1], label: "grueso", fill: "#fbeee9" },
] as const;

interface SizeReconciliationProps {
  range: LoadedRange;
  sizeUnit: SizeUnit;
}

export function SizeReconciliation({
  range,
  sizeUnit,
}: SizeReconciliationProps): JSX.Element | null {
  const series = range.reconciliation;

  if (!series || series.simulatedLine1P80In.length === 0) {
    return null;
  }

  const deltaSimulated = meanOfDifference(
    series.simulatedLine2P80In,
    series.simulatedLine1P80In,
  );
  const deltaMeasured = meanOfDifference(series.measuredLine2P80In, series.measuredLine1P80In);

  return (
    <figure className="reconciliation">
      <figcaption>
        <strong>Reconciliacion granulometrica</strong>
        <span>
          Media del rango. La diferencia entre lineas es lo unico comparable: simulada{" "}
          {formatSigned(toUnit(deltaSimulated, sizeUnit), sizeUnit === "mm" ? 1 : 3)}
          {unitSuffix(sizeUnit)} contra medida{" "}
          {formatSigned(toUnit(deltaMeasured, sizeUnit), sizeUnit === "mm" ? 1 : 3)}
          {unitSuffix(sizeUnit)}.
        </span>
      </figcaption>

      <div className="reconciliation-split">
        <LinePanel series={series} line={1} sizeUnit={sizeUnit} />
        <LinePanel series={series} line={2} sizeUnit={sizeUnit} />
      </div>

      <ul className="reconciliation-key">
        <li>
          <span className="swatch" style={{ background: COLOUR_LINE1 }} /> Linea A medida
        </li>
        <li>
          <span className="swatch" style={{ background: COLOUR_LINE2 }} /> Linea B medida
        </li>
        <li>
          <span className="swatch is-dashed" style={{ color: COLOUR_FEED }} /> Alimentacion,
          referencia
        </li>
        <li>
          <span className="swatch is-marker" style={{ background: COLOUR_SIMULATED }} /> P80
          simulado
        </li>
      </ul>

      <p className="reconciliation-note">
        La curva es <strong>enteramente medicion</strong>: el automata propaga un solo tamano por
        celda, de modo que su unica salida es el P80 marcado sobre el 80 %. El nivel absoluto
        tampoco es comparable, porque las camaras de descarga leen {formatSize(0.83, sizeUnit)}{" "}
        mas fino en F80 que la de entrada y el modelo se alimenta de esa medicion. Lo valido es la diferencia
        entre lineas.
      </p>
    </figure>
  );
}

/** Panel de una linea: su curva medida, la alimentacion y el P80 simulado. */
function LinePanel({
  series,
  line,
  sizeUnit,
}: {
  series: ReconciliationSeries;
  line: 1 | 2;
  sizeUnit: SizeUnit;
}): JSX.Element {
  const plotHeight = HEIGHT - MARGINS.top - MARGINS.bottom;
  const colour = line === 1 ? COLOUR_LINE1 : COLOUR_LINE2;
  const camera = line === 1 ? "sensor A" : "sensor B";

  /*
   * La escala se construye sobre el dominio YA convertido, de modo que las
   * marcas de decada caigan en numeros redondos de la unidad elegida -- 1, 2, 5,
   * 10 mm -- y no en pulgadas traducidas. Los datos se convierten al dibujar.
   */
  const domain: readonly [number, number] = [
    toUnit(SIZE_DOMAIN_IN[0], sizeUnit),
    toUnit(SIZE_DOMAIN_IN[1], sizeUnit),
  ];
  const scale = logScale(domain, [MARGINS.left, WIDTH - MARGINS.right]);
  const x = (inches: number): number => scale(toUnit(inches, sizeUnit));
  const y = linearScale([0, 100], [MARGINS.top + plotHeight, MARGINS.top]);

  const measured = decilePoints(series, `measuredLine${line}P`, `measuredLine${line}TopsizeIn`);
  const feed = decilePoints(series, "measuredFeedF", "measuredFeedTopsizeIn");
  const simulatedP80 = meanOf(series[`simulatedLine${line}P80In`] ?? []);
  const measuredP80 = meanOf(series[`measuredLine${line}P80In`] ?? []);

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="reconciliation-svg"
      role="img"
      aria-label={`Curva granulometrica de la linea ${line}`}
    >
      {ZONES.map((zone) => (
        <g key={zone.label}>
          <rect
            x={x(zone.from)}
            y={MARGINS.top}
            width={x(zone.to) - x(zone.from)}
            height={plotHeight}
            fill={zone.fill}
          />
          <text
            x={(x(zone.from) + x(zone.to)) / 2}
            y={MARGINS.top + 12}
            textAnchor="middle"
            className="axis-caption"
          >
            {zone.label}
          </text>
        </g>
      ))}

      {[FINE_CUT_IN, COARSE_CUT_IN].map((cut) => (
        <line
          key={cut}
          x1={x(cut)}
          x2={x(cut)}
          y1={MARGINS.top}
          y2={MARGINS.top + plotHeight}
          stroke="#c9d3d7"
        />
      ))}

      {y.ticks(5).map((tick) => (
        <g key={`p-${tick}`}>
          <line
            x1={MARGINS.left}
            x2={WIDTH - MARGINS.right}
            y1={y(tick)}
            y2={y(tick)}
            stroke="#e3e5e4"
          />
          <text x={MARGINS.left - 6} y={y(tick) + 4} textAnchor="end" className="axis-text">
            {tick.toFixed(0)}
          </text>
        </g>
      ))}

      {decadeTicks(domain[0], domain[1]).map((tick) => (
        <text
          key={`s-${tick}`}
          x={scale(tick)}
          y={HEIGHT - 22}
          textAnchor="middle"
          className="axis-text"
        >
          {formatTick(tick)}
        </text>
      ))}

      <line
        x1={MARGINS.left}
        x2={WIDTH - MARGINS.right}
        y1={y(80)}
        y2={y(80)}
        stroke="#98a4a8"
        strokeDasharray="4 3"
      />

      <Curve points={feed} x={x} y={y} colour={COLOUR_FEED} dashed />
      <Curve points={measured} x={x} y={y} colour={colour} />

      {Number.isFinite(simulatedP80) ? (
        <g>
          <line
            x1={x(simulatedP80)}
            x2={x(simulatedP80)}
            y1={y(80)}
            y2={MARGINS.top + plotHeight}
            stroke={COLOUR_SIMULATED}
            strokeWidth={2}
            strokeDasharray="5 3"
          />
          <circle cx={x(simulatedP80)} cy={y(80)} r={4} fill={COLOUR_SIMULATED} />
        </g>
      ) : null}

      <text x={MARGINS.left} y={MARGINS.top - 4} className="axis-text">
        Línea {line} – {camera === "sensor A" ? "Sensor A" : "Sensor B"}
      </text>
      <text x={WIDTH - MARGINS.right} y={HEIGHT - 6} textAnchor="end" className="axis-caption">
        tamano ({sizeUnit === "mm" ? "mm" : "pulgadas"}), escala log
      </text>
      <text x={MARGINS.left - 6} y={MARGINS.top - 4} textAnchor="end" className="axis-text">
        %
      </text>
      <text x={MARGINS.left} y={HEIGHT - 6} className="axis-caption">
        P80 medido {formatSize(measuredP80, sizeUnit)} – Simulado {formatSize(simulatedP80, sizeUnit)}
      </text>
    </svg>
  );
}

function Curve({
  points,
  x,
  y,
  colour,
  dashed = false,
}: {
  points: DecilePoint[];
  x: (value: number) => number;
  y: (value: number) => number;
  colour: string;
  dashed?: boolean;
}): JSX.Element | null {
  if (points.length === 0) {
    return null;
  }

  const path = points
    .map(
      (point, position) =>
        `${position === 0 ? "M" : "L"}${x(point.sizeIn).toFixed(1)} ${y(point.passingPct).toFixed(1)}`,
    )
    .join(" ");

  return (
    <g>
      <path
        d={path}
        fill="none"
        stroke={colour}
        strokeWidth={2}
        strokeDasharray={dashed ? "5 3" : undefined}
      />
      {points.map((point) => (
        <circle
          key={point.passingPct}
          cx={x(point.sizeIn)}
          cy={y(point.passingPct)}
          r={2.2}
          fill={colour}
        />
      ))}
    </g>
  );
}

interface DecilePoint {
  sizeIn: number;
  passingPct: number;
}

/** Puntos de la curva de una camara, del decil mas fino al tamano maximo. */
function decilePoints(
  series: ReconciliationSeries,
  prefix: string,
  topsizeKey: string,
): DecilePoint[] {
  const points: DecilePoint[] = [];

  for (const decile of DECILES) {
    const value = meanOf(series[`${prefix}${decile}In`] ?? []);

    if (Number.isFinite(value) && value > 0) {
      points.push({ sizeIn: value, passingPct: decile });
    }
  }

  const topsize = meanOf(series[topsizeKey] ?? []);

  if (Number.isFinite(topsize) && topsize > 0) {
    points.push({ sizeIn: topsize, passingPct: 100 });
  }

  return points;
}

/** Media de una serie ignorando huecos; `NaN` si no hay ningun valor. */
function meanOf(values: readonly (number | null)[]): number {
  let total = 0;
  let seen = 0;

  for (const value of values) {
    if (value === null || !Number.isFinite(value)) {
      continue;
    }

    total += value;
    seen += 1;
  }

  return seen > 0 ? total / seen : Number.NaN;
}

/** Media de la diferencia punto a punto, solo sobre los cuadros con ambos valores. */
function meanOfDifference(
  minuend: readonly (number | null)[],
  subtrahend: readonly (number | null)[],
): number {
  let total = 0;
  let seen = 0;

  for (const [position, value] of minuend.entries()) {
    const other = subtrahend[position];

    if (value === null || other === null || other === undefined) {
      continue;
    }

    total += value - other;
    seen += 1;
  }

  return seen > 0 ? total / seen : Number.NaN;
}
