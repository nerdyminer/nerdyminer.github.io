/**
 * Reconciliacion de la altura del acopio: simulada contra medida.
 *
 * Es la validacion mas directa del modelo. La medicion anonimizada registra una altura
 * real y el automata produce otra sobre la misma huella, de modo que la distancia
 * entre ambas curvas dice cuanto se aparta el acopio simulado del real sin
 * pasar por ningun supuesto de granulometria.
 *
 * Las barras
 * ----------
 * Bajo las curvas va el tonelaje no reconciliado entre las balanzas y el cambio
 * de inventario que explica el modelo. Crece durante transitorios y starving,
 * cuando errores de soporte temporal y material fuera de la carga viva pesan mas.
 *
 * Es la huella de lo que el modelo no representa. Una barra visible es
 * material cuyo destino no queda cerrado; en un caso real obligaria a
 * investigar instrumentacion y practicas operacionales antes de recalibrar.
 */

import type { LoadedRange } from "../frames";
import { formatNumber } from "../theme";
import {
  DEFAULT_MARGINS,
  axisLabel,
  extentOf,
  linePath,
  linearScale,
  padExtent,
} from "./chartAxes";

const WIDTH = 1120;
const HEIGHT = 300;
/** Fraccion de la altura reservada a las barras de balance, bajo las curvas. */
const BAR_BAND = 0.28;

const COLOUR_MEASURED = "#434444";
const COLOUR_SIMULATED = "#007ED3";
const COLOUR_UNMODELLED = "#E8B22C";

interface HeightReconciliationProps {
  range: LoadedRange;
  frameIndex: number;
  /** Altura de diseno; `null` cuando el export no la declara. */
  designHeightM: number | null;
  onFrameChange: (position: number) => void;
}

export function HeightReconciliation({
  range,
  frameIndex,
  designHeightM,
  onFrameChange,
}: HeightReconciliationProps): JSX.Element | null {
  const series = range.reconciliation;

  if (!series) {
    return null;
  }

  const simulated = series.simulatedHeightM;
  const measured = series.measuredHeightM;
  const unmodelled = series.unmodelledT;
  const count = simulated.length;

  if (count === 0) {
    return null;
  }

  const margins = DEFAULT_MARGINS;
  const plotWidth = WIDTH - margins.left - margins.right;
  const plotHeight = HEIGHT - margins.top - margins.bottom;
  const barTop = margins.top + plotHeight * (1 - BAR_BAND);
  const lineBottom = barTop - 8;

  const x = (position: number): number =>
    margins.left + (count <= 1 ? plotWidth / 2 : (position / (count - 1)) * plotWidth);

  const heightDomain = padExtent(
    extentOf(simulated, measured, designHeightM === null ? [] : [designHeightM]),
  );
  const y = linearScale(heightDomain, [lineBottom, margins.top]);

  const peakUnmodelled = Math.max(
    ...unmodelled.map((value) => (value === null ? 0 : Math.abs(value))),
    1e-6,
  );
  const barScale = linearScale([0, peakUnmodelled], [0, plotHeight * BAR_BAND - 6]);

  const totalUnmodelledT = unmodelled.reduce<number>(
    (total, value) => total + (value ?? 0),
    0,
  );
  const residuals = simulated
    .map((value, position) =>
      value === null || measured[position] === null ? null : value - measured[position]!,
    )
    .filter((value): value is number => value !== null);
  const meanResidual =
    residuals.length > 0
      ? residuals.reduce((total, value) => total + value, 0) / residuals.length
      : Number.NaN;

  const barWidth = Math.max(1, plotWidth / count - 0.5);

  return (
    <figure className="reconciliation">
      <figcaption>
        <strong>Reconciliacion de altura del acopio</strong>
        <span>
          Medición del escenario pedagógico sobre el corredor de extracción contra la huella equivalente del modelo. Sesgo medio{" "}
          {Number.isFinite(meanResidual) ? `${meanResidual >= 0 ? "+" : ""}${formatNumber(meanResidual, 2)} m` : "n/d"}{" "}
          en el rango.
        </span>
      </figcaption>

      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="reconciliation-svg"
        role="img"
        aria-label="Altura simulada contra medida, con el tonelaje no modelado en barras"
        onClick={(event) => {
          const box = event.currentTarget.getBoundingClientRect();
          const ratio = (event.clientX - box.left) / box.width;
          const position = Math.round(ratio * WIDTH);
          const fraction = (position - margins.left) / plotWidth;
          onFrameChange(Math.min(count - 1, Math.max(0, Math.round(fraction * (count - 1)))));
        }}
      >
        {y.ticks(5).map((tick) => (
          <g key={`h-${tick}`}>
            <line
              x1={margins.left}
              x2={WIDTH - margins.right}
              y1={y(tick)}
              y2={y(tick)}
              stroke="#e3e5e4"
            />
            <text x={margins.left - 6} y={y(tick) + 4} textAnchor="end" className="axis-text">
              {axisLabel(tick)}
            </text>
          </g>
        ))}

        {/* Altura de diseno: por sobre ella el acopio simulado deja de ser fisico. */}
        {designHeightM === null ? null : (
          <>
            <line
              x1={margins.left}
              x2={WIDTH - margins.right}
              y1={y(designHeightM)}
              y2={y(designHeightM)}
              stroke="#D37154"
              strokeDasharray="6 4"
            />
            <text x={WIDTH - margins.right + 4} y={y(designHeightM) + 4} className="axis-text">
              diseno
            </text>
          </>
        )}

        {unmodelled.map((value, position) =>
          value === null || value <= 0 ? null : (
            <rect
              key={`bar-${position}`}
              x={x(position) - barWidth / 2}
              y={barTop}
              width={barWidth}
              height={barScale(value)}
              fill={COLOUR_UNMODELLED}
              opacity={0.85}
            />
          ),
        )}

        <line
          x1={margins.left}
          x2={WIDTH - margins.right}
          y1={barTop}
          y2={barTop}
          stroke="#bac4c8"
        />
        <text x={margins.left - 6} y={barTop + 4} textAnchor="end" className="axis-text">
          0
        </text>
        <text
          x={WIDTH - margins.right + 4}
          y={barTop + 14}
          className="axis-text"
        >
          t/cuadro
        </text>

        <path d={linePath(measured, x, y)} fill="none" stroke={COLOUR_MEASURED} strokeWidth={1.8} />
        <path
          d={linePath(simulated, x, y)}
          fill="none"
          stroke={COLOUR_SIMULATED}
          strokeWidth={1.8}
        />

        <line
          x1={x(frameIndex)}
          x2={x(frameIndex)}
          y1={margins.top}
          y2={margins.top + plotHeight}
          stroke="#1C434B"
          strokeWidth={1}
          opacity={0.55}
        />

        <text x={margins.left} y={HEIGHT - 8} className="axis-text">
          {range.fromDay}
        </text>
        <text x={WIDTH - margins.right} y={HEIGHT - 8} textAnchor="end" className="axis-text">
          {range.toDay}
        </text>
        <text
          x={margins.left - 6}
          y={margins.top - 4}
          textAnchor="end"
          className="axis-text"
        >
          m
        </text>
      </svg>

      <ul className="reconciliation-key">
        <li>
          <span className="swatch" style={{ background: COLOUR_MEASURED }} /> Altura medida
        </li>
        <li>
          <span className="swatch" style={{ background: COLOUR_SIMULATED }} /> Altura simulada
        </li>
        <li>
          <span className="swatch" style={{ background: COLOUR_UNMODELLED }} /> Balance no
          modelado
        </li>
      </ul>

      <p className="reconciliation-note">
        <strong>
          Las barras son mineral que el modelo no explica:{" "}
          {formatNumber(totalUnmodelledT / 1000, 1)} kt en este rango.
        </strong>{" "}
        Las balanzas dicen que entro mas material del que el acopio puede contener. Puede existir
        un flujo omitido o una inconsistencia instrumental: donde hay barra, hay material cuya
        trayectoria el modelo desconoce y una hipotesis que debe investigarse antes de recalibrar.
      </p>
    </figure>
  );
}
