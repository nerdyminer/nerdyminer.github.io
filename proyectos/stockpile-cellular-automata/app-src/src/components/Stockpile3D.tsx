/**
 * Vista tridimensional del acopio con camara orbitable.
 *
 * El acopio es un campo de alturas sobre una grilla regular, de modo que no hace
 * falta un motor 3D completo: basta proyectar cada columna como un prisma y
 * dibujarlas de atras hacia adelante para que el algoritmo del pintor resuelva
 * la oclusion. Eso evita una dependencia de varios cientos de kilobytes y
 * mantiene el control total sobre el color, que aqui codifica granulometria y es
 * el mensaje de la figura.
 *
 * Proyeccion
 * ----------
 * Con azimut ``theta`` y elevacion ``phi``, cada punto del mundo se lleva a
 * pantalla mediante:
 *
 *     derecha    = x cos(theta) + y sin(theta)
 *     adelante   = -x sin(theta) + y cos(theta)
 *     pantallaX  = derecha
 *     pantallaY  = adelante sin(phi) - z cos(phi)
 *
 * Con ``phi`` de 90 grados la vista queda cenital y con ``phi`` de 0 queda a ras
 * de suelo.
 *
 * Orden de dibujo
 * ---------------
 * ``adelante`` crece hacia el observador, de modo que las columnas se dibujan de
 * menor a mayor: primero el fondo y encima el frente. Invertir este orden hace
 * que la pared trasera del acopio se pinte sobre todo lo demas y la figura se
 * vea hueca y del reves.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import type { ColourMapId } from "../colormaps";
import { colourScale } from "../colormaps";
import type { FeederInfo, Frame, FramesIndex } from "../frames";

interface Stockpile3DProps {
  index: FramesIndex;
  frame: Frame;
  width: number;
  height: number;
  verticalExaggeration: number;
  showFeeders: boolean;
  colourMapId: ColourMapId;
}

interface Camera {
  azimuthDeg: number;
  elevationDeg: number;
  zoom: number;
}

const DEFAULT_CAMERA: Camera = { azimuthDeg: 35, elevationDeg: 34, zoom: 1 };
const MIN_ELEVATION_DEG = 4;
const MAX_ELEVATION_DEG = 88;
const FEEDER_MARKER_RADIUS = 5;
const MINIMUM_ZOOM = 0.4;
const MAXIMUM_ZOOM = 3;
const ZOOM_STEP = 1.15;

export function Stockpile3D({
  index,
  frame,
  width,
  height,
  verticalExaggeration,
  showFeeders,
  colourMapId,
}: Stockpile3DProps): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [camera, setCamera] = useState<Camera>(DEFAULT_CAMERA);
  const dragRef = useRef<{ x: number; y: number } | null>(null);

  const onPointerDown = useCallback((event: React.PointerEvent<HTMLCanvasElement>) => {
    dragRef.current = { x: event.clientX, y: event.clientY };
    event.currentTarget.setPointerCapture(event.pointerId);
  }, []);

  const onPointerMove = useCallback((event: React.PointerEvent<HTMLCanvasElement>) => {
    const origin = dragRef.current;

    if (!origin) {
      return;
    }

    const deltaX = event.clientX - origin.x;
    const deltaY = event.clientY - origin.y;
    dragRef.current = { x: event.clientX, y: event.clientY };

    setCamera((current) => ({
      ...current,
      azimuthDeg: (current.azimuthDeg + deltaX * 0.4) % 360,
      // Arrastrar hacia arriba sube la camara y deja ver el acopio desde mas
      // alto, que es como responde cualquier visor orbital. Con el signo
      // contrario la figura giraba al reves de la mano.
      elevationDeg: Math.min(
        MAX_ELEVATION_DEG,
        Math.max(MIN_ELEVATION_DEG, current.elevationDeg + deltaY * 0.3),
      ),
    }));
  }, []);

  const onPointerUp = useCallback((event: React.PointerEvent<HTMLCanvasElement>) => {
    dragRef.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
  }, []);

  const applyZoom = useCallback((factor: number) => {
    setCamera((current) => ({
      ...current,
      zoom: Math.min(MAXIMUM_ZOOM, Math.max(MINIMUM_ZOOM, current.zoom * factor)),
    }));
  }, []);

  /*
   * La rueda solo hace zoom con Ctrl o Cmd pulsado, y en ese caso se cancela el
   * desplazamiento de la pagina. Sin el modificador la rueda desplaza la pagina
   * con normalidad.
   *
   * El lienzo ocupa mas de mil pixeles de alto: capturar la rueda sin condicion
   * dejaria al usuario atrapado, incapaz de bajar por el documento con el puntero
   * sobre la vista. Y capturarla sin cancelar el evento produce lo contrario, que
   * es lo que ocurria antes: la pagina se desplazaba mientras la vista hacia zoom.
   *
   * El listener se registra a mano porque React entrega los eventos de rueda en
   * modo pasivo, donde `preventDefault` no tiene efecto.
   */
  useEffect(() => {
    const canvas = canvasRef.current;

    if (!canvas) {
      return;
    }

    const onWheel = (event: WheelEvent): void => {
      if (!event.ctrlKey && !event.metaKey) {
        return;
      }

      event.preventDefault();
      applyZoom(event.deltaY > 0 ? 1 / ZOOM_STEP : ZOOM_STEP);
    };

    canvas.addEventListener("wheel", onWheel, { passive: false });

    return () => canvas.removeEventListener("wheel", onWheel);
  }, [applyZoom]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");

    if (!canvas || !context) {
      return;
    }

    draw(context, canvas, index, frame, camera, {
      width,
      height,
      verticalExaggeration,
      showFeeders,
      sizeColour: colourScale(colourMapId),
    });
  }, [index, frame, camera, width, height, verticalExaggeration, showFeeders, colourMapId]);

  return (
    <div className="viewport">
      <canvas
        ref={canvasRef}
        style={{ width: "100%", height: "auto", aspectRatio: `${width} / ${height}`, touchAction: "none", cursor: "grab" }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      />
      <div className="viewport-overlay">
        <span>
          Azimut {Math.round(((camera.azimuthDeg % 360) + 360) % 360)}&deg; – Elevación{" "}
          {Math.round(camera.elevationDeg)}&deg;
        </span>
        <button type="button" onClick={() => applyZoom(ZOOM_STEP)} aria-label="Acercar">
          +
        </button>
        <button type="button" onClick={() => applyZoom(1 / ZOOM_STEP)} aria-label="Alejar">
          &minus;
        </button>
        <button type="button" onClick={() => setCamera(DEFAULT_CAMERA)}>
          Restablecer vista
        </button>
      </div>
      <p className="viewport-hint">
        Arrastrar para orbitar. Ctrl y rueda, o los botones, para acercar; la rueda sola desplaza
        la pagina.
      </p>
    </div>
  );
}

interface DrawOptions {
  width: number;
  height: number;
  verticalExaggeration: number;
  showFeeders: boolean;
  sizeColour: (fraction: number) => string;
}

function draw(
  context: CanvasRenderingContext2D,
  canvas: HTMLCanvasElement,
  index: FramesIndex,
  frame: Frame,
  camera: Camera,
  options: DrawOptions,
): void {
  const { width, height, verticalExaggeration, showFeeders, sizeColour } = options;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, width, height);

  const { nEast, nNorth, cellSizeM, centreEast, centreNorth } = index.grid;
  const azimuth = (camera.azimuthDeg * Math.PI) / 180;
  const elevation = (camera.elevationDeg * Math.PI) / 180;
  const cosAzimuth = Math.cos(azimuth);
  const sinAzimuth = Math.sin(azimuth);
  const sinElevation = Math.sin(elevation);
  const cosElevation = Math.cos(elevation);
  const geometryRotation = ((index.rotationDeg ?? 0) * Math.PI) / 180;
  const cosGeometry = Math.cos(geometryRotation);
  const sinGeometry = Math.sin(geometryRotation);

  const rotateGeometry = (x: number, y: number): [number, number] => [
    x * cosGeometry - y * sinGeometry,
    x * sinGeometry + y * cosGeometry,
  ];

  const span = Math.max(nEast, nNorth) * cellSizeM;
  const scale = ((Math.min(width, height) * 0.78) / span) * camera.zoom;
  const originX = width / 2;
  const originY = height * 0.58;
  const [minSize, maxSize] = index.sizeRangeIn;
  const sizeSpan = Math.max(maxSize - minSize, 1e-6);

  const project = (worldX: number, worldY: number, worldZ: number): [number, number] => {
    const right = worldX * cosAzimuth + worldY * sinAzimuth;
    const forward = -worldX * sinAzimuth + worldY * cosAzimuth;

    return [
      originX + right * scale,
      originY + (forward * sinElevation - worldZ * verticalExaggeration * cosElevation) * scale,
    ];
  };

  const order: number[] = [];

  for (let north = 0; north < nNorth; north += 1) {
    for (let east = 0; east < nEast; east += 1) {
      order.push(north * nEast + east);
    }
  }

  order.sort((left, right) => forwardOf(left) - forwardOf(right));

  function forwardOf(cellIndex: number): number {
    const north = Math.floor(cellIndex / nEast);
    const east = cellIndex % nEast;
    const [worldX, worldY] = rotateGeometry(
      (east - centreEast) * cellSizeM,
      (north - centreNorth) * cellSizeM,
    );

    return -worldX * sinAzimuth + worldY * cosAzimuth;
  }

  const half = cellSizeM / 2;

  for (const cellIndex of order) {
    const elevationM = frame.height[cellIndex]! / index.scales.height;

    if (elevationM <= 0) {
      continue;
    }

    const north = Math.floor(cellIndex / nEast);
    const east = cellIndex % nEast;
    const sourceX = (east - centreEast) * cellSizeM;
    const sourceY = (north - centreNorth) * cellSizeM;
    const size = frame.columnSize[cellIndex]! / index.scales.size;
    const colour = sizeColour(size > 0 ? (size - minSize) / sizeSpan : Number.NaN);

    const corners = [
      rotateGeometry(sourceX - half, sourceY - half),
      rotateGeometry(sourceX + half, sourceY - half),
      rotateGeometry(sourceX + half, sourceY + half),
      rotateGeometry(sourceX - half, sourceY + half),
    ];
    const topCorners = corners.map(([x, y]) => project(x, y, elevationM));
    const baseCorners = corners.map(([x, y]) => project(x, y, 0));

    for (let corner = 0; corner < 4; corner += 1) {
      const next = (corner + 1) % 4;
      const a = topCorners[corner]!;
      const b = topCorners[next]!;
      const c = baseCorners[next]!;
      const d = baseCorners[corner]!;

      if ((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) <= 0) {
        continue;
      }

      context.fillStyle = shade(colour, 0.55 + corner * 0.06);
      context.beginPath();
      context.moveTo(a[0], a[1]);
      context.lineTo(b[0], b[1]);
      context.lineTo(c[0], c[1]);
      context.lineTo(d[0], d[1]);
      context.closePath();
      context.fill();
    }

    context.fillStyle = colour;
    context.beginPath();
    context.moveTo(topCorners[0]![0], topCorners[0]![1]);

    for (let corner = 1; corner < 4; corner += 1) {
      context.lineTo(topCorners[corner]![0], topCorners[corner]![1]);
    }

    context.closePath();
    context.fill();
  }

  if (showFeeders) {
    drawInfrastructure(context, index, frame, project);
  }
}

/**
 * Dibuja los puntos de extraccion sobre la base del acopio.
 *
 * Se pintan siempre, incluso cuando quedan bajo el material, porque su posicion
 * respecto del eje es lo que explica el flujo: la fila mas alejada recupera
 * desde la periferia, que el flujo superficial deja mas gruesa.
 */
function drawInfrastructure(
  context: CanvasRenderingContext2D,
  index: FramesIndex,
  frame: Frame,
  project: (x: number, y: number, z: number) => [number, number],
): void {
  const { cellSizeM, centreEast, centreNorth } = index.grid;

  if (index.conveyor) {
    const bearing = (index.conveyor.bearingDeg * Math.PI) / 180;
    const reach = Math.min(index.grid.nEast, index.grid.nNorth) * cellSizeM * 0.46;
    const inclination = ((index.conveyor.inclinationDeg ?? 15) * Math.PI) / 180;
    let apexHeightM = 0;
    for (const encodedHeight of frame.height) {
      apexHeightM = Math.max(apexHeightM, encodedHeight / index.scales.height);
    }
    /*
     * La correa es infraestructura fija. Su cabeza se ancla a la cota de
     * diseño pública y no al ápice instantáneo: el stockpile puede crecer o
     * vaciarse bajo ella, pero la estructura no acompaña ese movimiento.
     * Sólo el extremo inferior de la caída libre sigue la superficie.
     */
    const designHeightM =
      index.designHeightM ??
      index.grid.nVertical * (index.grid.verticalCellSizeM ?? index.grid.cellSizeM);
    const headZ = designHeightM + (index.conveyor.dischargeClearanceM ?? 1.32);
    const tailZ = Math.max(2, headZ - Math.tan(inclination) * reach);
    const tailX = -Math.sin(bearing) * reach;
    const tailY = -Math.cos(bearing) * reach;
    const start = project(tailX, tailY, tailZ);
    const end = project(0, 0, headZ);

    context.save();
    // Dos pórticos visibles en el tramo exterior fijan la cota de la correa.
    for (const fraction of [0.08, 0.27]) {
      const x = tailX * (1 - fraction);
      const y = tailY * (1 - fraction);
      const z = tailZ + (headZ - tailZ) * fraction;
      const base = project(x, y, 0);
      const top = project(x, y, z);
      context.strokeStyle = "rgba(38, 62, 68, 0.72)";
      context.lineWidth = 2;
      context.beginPath();
      context.moveTo(base[0] - 5, base[1]);
      context.lineTo(top[0], top[1]);
      context.lineTo(base[0] + 5, base[1]);
      context.stroke();
    }

    context.strokeStyle = "rgba(28, 20, 31, 0.68)";
    context.lineWidth = 9;
    context.beginPath();
    context.moveTo(start[0], start[1]);
    context.lineTo(end[0], end[1]);
    context.stroke();
    context.strokeStyle = "#9b1b72";
    context.lineWidth = 5;
    context.stroke();
    context.strokeStyle = "#f3a8d5";
    context.lineWidth = 1;
    context.stroke();

    context.fillStyle = "#9b1b72";
    context.beginPath();
    context.arc(end[0], end[1], 7, 0, Math.PI * 2);
    context.fill();
    context.strokeStyle = "#ffffff";
    context.lineWidth = 2;
    context.stroke();

    // El tramo ámbar es la caída libre desde la cabeza de la correa al ápice.
    const impact = project(0, 0, apexHeightM);
    context.strokeStyle = "#f0b429";
    context.lineWidth = 3;
    context.setLineDash([3, 4]);
    context.beginPath();
    context.moveTo(end[0], end[1] + 4);
    context.lineTo(impact[0], impact[1]);
    context.stroke();
    context.setLineDash([]);

    const labelX = start[0] + (end[0] - start[0]) * 0.42;
    const labelY = start[1] + (end[1] - start[1]) * 0.42 - 14;
    context.font = "700 12px Inter, Arial, sans-serif";
    const label = "CORREA ELEVADA";
    const labelWidth = context.measureText(label).width + 18;
    context.fillStyle = "rgba(7, 24, 29, 0.88)";
    context.beginPath();
    context.roundRect(labelX - labelWidth / 2, labelY - 14, labelWidth, 22, 7);
    context.fill();
    context.fillStyle = "#f7d5ea";
    context.textAlign = "center";
    context.fillText(label, labelX, labelY + 1);
    context.restore();
  }

  const byLine = new Map<number, FeederInfo[]>();

  for (const feeder of index.feeders) {
    byLine.set(feeder.line, [...(byLine.get(feeder.line) ?? []), feeder]);
  }

  for (const [line, feeders] of byLine) {
    const colour = line === 1 ? "#007ED3" : "#E97132";
    const points = feeders.map((feeder) =>
      project(
        (feeder.east - centreEast) * cellSizeM,
        (feeder.north - centreNorth) * cellSizeM,
        0,
      ),
    );

    context.strokeStyle = colour;
    context.lineWidth = 2;
    context.setLineDash([6, 4]);
    context.beginPath();
    context.moveTo(points[0]![0], points[0]![1]);

    for (let index = 1; index < points.length; index += 1) {
      context.lineTo(points[index]![0], points[index]![1]);
    }

    context.stroke();
    context.setLineDash([]);

    for (const [index, point] of points.entries()) {
      context.beginPath();
      context.arc(point[0], point[1], FEEDER_MARKER_RADIUS, 0, Math.PI * 2);
      context.fillStyle = colour;
      context.fill();
      context.strokeStyle = "#ffffff";
      context.lineWidth = 2;
      context.stroke();

      context.fillStyle = "#434444";
      context.font = "600 10px Calibri, sans-serif";
      context.textAlign = "center";
      context.fillText(feeders[index]!.name, point[0], point[1] + 17);
    }
  }
}

/** Oscurece un color `rgb(...)` por un factor multiplicativo. */
function shade(colour: string, factor: number): string {
  const parsed = colour.match(/\d+/g);

  if (!parsed || parsed.length < 3) {
    return colour;
  }

  const channels = parsed
    .slice(0, 3)
    .map((value) => Math.round(Math.min(255, Number(value) * factor)))
    .join(", ");

  return `rgb(${channels})`;
}
