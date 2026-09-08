/**
 * Vistas ortogonales del acopio: planta y los dos cortes verticales por el eje.
 *
 * La vista en planta muestra el tamano medio de cada columna y es donde se lee
 * la segregacion radial. Los dos cortes verticales muestran la estructura
 * interna: el grueso acumulado en las zonas estancas del fondo y la zona viva
 * sobre los puntos de extraccion, que ningun instrumento del acopio puede
 * muestrear.
 *
 * Se dibujan en canvas y no en SVG porque cada vista tiene entre mil quinientas
 * y dos mil seiscientas celdas y se redibujan a cada cuadro de la animacion.
 */

import { useEffect, useRef } from "react";

import type { ColourMapId } from "../colormaps";
import { colourScale } from "../colormaps";
import type { Frame, FramesIndex } from "../frames";

export type Plane = "plan" | "sectionEast" | "sectionNorth";

interface OrthogonalViewProps {
  index: FramesIndex;
  frame: Frame;
  plane: Plane;
  width: number;
  height: number;
  showFeeders: boolean;
  colourMapId: ColourMapId;
}

const EMPTY_FILL = 0.02;

/** Ancho reservado a la izquierda de los cortes para la regla de altura. */
const RULER_WIDTH = 34;

export function OrthogonalView({
  index,
  frame,
  plane,
  width,
  height,
  showFeeders,
  colourMapId,
}: OrthogonalViewProps): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");

    if (!canvas || !context) {
      return;
    }

    const ratio = window.devicePixelRatio || 1;
    canvas.width = width * ratio;
    canvas.height = height * ratio;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, width, height);

    const colour = colourScale(colourMapId);

    if (plane === "plan") {
      drawPlan(context, index, frame, width, height, showFeeders, colour);
    } else {
      drawSection(context, index, frame, plane, width, height, showFeeders, colour);
    }
  }, [index, frame, plane, width, height, showFeeders, colourMapId]);

  return (
    <canvas
      ref={canvasRef}
      style={{ width: "100%", height: "auto", aspectRatio: `${width} / ${height}`, display: "block" }}
    />
  );
}

/** Vista en planta: tamano medio por columna sobre el plano Este-Norte. */
function drawPlan(
  context: CanvasRenderingContext2D,
  index: FramesIndex,
  frame: Frame,
  width: number,
  height: number,
  showFeeders: boolean,
  sizeColour: (fraction: number) => string,
): void {
  const { nEast, nNorth } = index.grid;
  const cell = Math.min(width / nEast, height / nNorth) / Math.SQRT2;
  const centreX = width / 2;
  const centreY = height / 2;
  const angle = -((index.rotationDeg ?? 0) * Math.PI) / 180;
  const [minSize, maxSize] = index.sizeRangeIn;
  const span = Math.max(maxSize - minSize, 1e-6);

  context.save();
  context.translate(centreX, centreY);
  context.rotate(angle);
  for (let north = 0; north < nNorth; north += 1) {
    for (let east = 0; east < nEast; east += 1) {
      const cellIndex = north * nEast + east;
      const elevation = frame.height[cellIndex] ?? 0;

      if (elevation <= 0) {
        continue;
      }

      const size = (frame.columnSize[cellIndex] ?? 0) / index.scales.size;
      context.fillStyle = sizeColour(size > 0 ? (size - minSize) / span : Number.NaN);
      context.fillRect(
        (east - nEast / 2) * cell,
        (nNorth / 2 - 1 - north) * cell,
        cell + 0.5,
        cell + 0.5,
      );
    }
  }
  context.restore();

  if (!showFeeders) {
    return;
  }

  for (const feeder of index.feeders) {
    const x = centreX + (feeder.east - index.grid.centreEast) * cell;
    const y = centreY - (feeder.north - index.grid.centreNorth) * cell;
    context.beginPath();
    context.arc(x, y, 4.5, 0, Math.PI * 2);
    context.fillStyle = feeder.line === 1 ? "#007ED3" : "#E97132";
    context.fill();
    context.strokeStyle = "#ffffff";
    context.lineWidth = 1.5;
    context.stroke();
  }
}

/**
 * Corte vertical por el eje del cono.
 *
 * `sectionEast` corta a lo largo del eje Este y `sectionNorth` a lo largo del
 * Norte. Cada celda se pinta con su tamano propio, no con el promedio de la
 * columna: es la unica vista que expone la estratificacion interna.
 */
function drawSection(
  context: CanvasRenderingContext2D,
  index: FramesIndex,
  frame: Frame,
  plane: Exclude<Plane, "plan">,
  width: number,
  height: number,
  showFeeders: boolean,
  sizeColour: (fraction: number) => string,
): void {
  const { nEast, nNorth, nVertical, cellSizeM } = index.grid;
  const verticalCellSizeM = index.grid.verticalCellSizeM ?? cellSizeM;
  const across = plane === "sectionEast" ? nEast : nNorth;
  const sizes = plane === "sectionEast" ? frame.sectionEastSize : frame.sectionNorthSize;
  const fills = plane === "sectionEast" ? frame.sectionEastFill : frame.sectionNorthFill;

  const cell = Math.min((width - RULER_WIDTH) / across, (height - 18) / nVertical);
  const offsetX = RULER_WIDTH + (width - RULER_WIDTH - cell * across) / 2;
  const baseY = height - 14;
  const [minSize, maxSize] = index.sizeRangeIn;
  const span = Math.max(maxSize - minSize, 1e-6);

  for (let lateral = 0; lateral < across; lateral += 1) {
    for (let level = 0; level < nVertical; level += 1) {
      const cellIndex = lateral * nVertical + level;
      const fill = (fills[cellIndex] ?? 0) / index.scales.fill;

      if (fill <= EMPTY_FILL) {
        continue;
      }

      const size = (sizes[cellIndex] ?? 0) / index.scales.size;
      context.globalAlpha = 0.35 + 0.65 * Math.min(1, fill);
      context.fillStyle = sizeColour(size > 0 ? (size - minSize) / span : Number.NaN);
      context.fillRect(
        offsetX + lateral * cell,
        baseY - (level + 1) * cell,
        cell + 0.5,
        cell + 0.5,
      );
    }
  }

  context.globalAlpha = 1;
  context.strokeStyle = "#5b6b70";
  context.lineWidth = 1;
  context.beginPath();
  context.moveTo(offsetX, baseY);
  context.lineTo(offsetX + across * cell, baseY);
  context.stroke();

  drawHeightRuler(context, {
    baseY,
    metresPerPixel: verticalCellSizeM / cell,
    topY: baseY - nVertical * cell,
    rightX: offsetX,
    plotRight: offsetX + across * cell,
  });

  if (!showFeeders) {
    return;
  }

  for (const feeder of index.feeders) {
    const angle = ((index.rotationDeg ?? 0) * Math.PI) / 180;
    const publicEast = feeder.east - index.grid.centreEast;
    const publicNorth = feeder.north - index.grid.centreNorth;
    const sourceEast = publicEast * Math.cos(angle) + publicNorth * Math.sin(angle);
    const sourceNorth = -publicEast * Math.sin(angle) + publicNorth * Math.cos(angle);
    const lateral =
      plane === "sectionEast"
        ? index.grid.centreEast + sourceEast
        : index.grid.centreNorth + sourceNorth;
    const x = offsetX + (lateral + 0.5) * cell;
    context.beginPath();
    context.moveTo(x - 5, baseY + 9);
    context.lineTo(x + 5, baseY + 9);
    context.lineTo(x, baseY + 1);
    context.closePath();
    context.fillStyle = feeder.line === 1 ? "#007ED3" : "#E97132";
    context.fill();
  }
}

interface RulerGeometry {
  /** Coordenada de pantalla de la cota cero. */
  baseY: number;
  /** Metros de acopio por pixel de pantalla. */
  metresPerPixel: number;
  /** Coordenada de pantalla del techo de la grilla. */
  topY: number;
  /** Borde derecho de la regla, donde empieza el corte. */
  rightX: number;
  /** Borde derecho del corte, hasta donde llegan las lineas de guia. */
  plotRight: number;
}

/**
 * Regla de altura al costado de un corte vertical.
 *
 * Sin ella el corte se lee como una figura sin escala: se ve que una zona es
 * mas alta que otra, pero no cuanto, y la altura del acopio es justamente la
 * variable que se reconcilia contra el sensor. El paso se elige de la serie
 * 1-2-5-10 para que las marcas caigan en numeros redondos con cualquier
 * exageracion de la vista.
 */
function drawHeightRuler(context: CanvasRenderingContext2D, geometry: RulerGeometry): void {
  const { baseY, metresPerPixel, topY, rightX, plotRight } = geometry;
  const spanM = (baseY - topY) * metresPerPixel;

  if (!Number.isFinite(spanM) || spanM <= 0) {
    return;
  }

  const step = niceStep(spanM / 6);

  context.save();
  context.strokeStyle = "#9aa8ad";
  context.fillStyle = "#5b6b70";
  context.lineWidth = 1;
  context.font = "10px Arial, sans-serif";
  context.textAlign = "right";
  context.textBaseline = "middle";

  context.beginPath();
  context.moveTo(rightX - 4, baseY);
  context.lineTo(rightX - 4, topY);
  context.stroke();

  for (let metres = 0; metres <= spanM + 1e-9; metres += step) {
    const y = baseY - metres / metresPerPixel;

    context.beginPath();
    context.moveTo(rightX - 9, y);
    context.lineTo(rightX - 4, y);
    context.stroke();

    // Guia tenue sobre el corte: permite leer la cota de una cresta sin
    // desplazar la mirada hasta el borde.
    context.save();
    context.globalAlpha = 0.18;
    context.beginPath();
    context.moveTo(rightX, y);
    context.lineTo(plotRight, y);
    context.stroke();
    context.restore();

    context.fillText(`${metres.toFixed(0)}`, rightX - 11, y);
  }

  context.textAlign = "left";
  context.fillText("m", 2, topY - 2);
  context.restore();
}

/** Paso de marca redondeado a la serie 1-2-5-10. */
function niceStep(raw: number): number {
  if (!Number.isFinite(raw) || raw <= 0) {
    return 1;
  }

  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const normalised = raw / magnitude;
  const step = normalised <= 1 ? 1 : normalised <= 2 ? 2 : normalised <= 5 ? 5 : 10;

  return step * magnitude;
}
