/**
 * Utilidades de escala y ejes para los graficos de reconciliacion.
 *
 * Los graficos se dibujan como SVG a mano en lugar de con una libreria. Son dos
 * figuras de forma conocida sobre series de a lo mas 672 puntos, y una libreria
 * de graficos anadiria varios cientos de kilobytes para resolver un problema
 * que aqui son cuarenta lineas. A
 * cambio, el cursor de la animacion y el grafico comparten exactamente el mismo
 * sistema de coordenadas sin tener que sincronizar dos motores de dibujo.
 */

export interface Margins {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

export const DEFAULT_MARGINS: Margins = { top: 14, right: 58, bottom: 26, left: 48 };

export interface LinearScale {
  /** Lleva un valor del dominio a coordenada de pantalla. */
  (value: number): number;
  domain: readonly [number, number];
  ticks: (count: number) => number[];
}

/**
 * Construye una escala lineal.
 *
 * @param domain Extremos del dominio. Un dominio degenerado se ensancha para no
 *   dividir por cero ni colapsar la serie sobre una sola linea.
 * @param range Extremos en pantalla, que para el eje vertical van invertidos.
 */
export function linearScale(
  domain: readonly [number, number],
  range: readonly [number, number],
): LinearScale {
  let [low, high] = domain;

  if (!Number.isFinite(low) || !Number.isFinite(high)) {
    [low, high] = [0, 1];
  }

  if (high - low < 1e-9) {
    const pad = Math.abs(high) > 1e-9 ? Math.abs(high) * 0.1 : 0.5;
    low -= pad;
    high += pad;
  }

  const [start, end] = range;
  const scale = ((value: number) =>
    start + ((value - low) / (high - low)) * (end - start)) as LinearScale;

  Object.defineProperty(scale, "domain", { value: [low, high] as const });
  Object.defineProperty(scale, "ticks", {
    value: (count: number) => niceTicks(low, high, count),
  });

  return scale;
}

/**
 * Construye una escala logaritmica.
 *
 * La granulometria abarca del orden de 0.05 a 20 pulgadas, casi tres decadas.
 * En escala lineal el extremo fino queda aplastado contra el eje y toda la
 * informacion de los primeros deciles se pierde, que es justo la zona donde se
 * decide la molienda. El logaritmo es la lectura natural de una curva
 * granulometrica.
 *
 * @param domain Extremos del dominio, ambos estrictamente positivos.
 * @param range Extremos en pantalla.
 */
export function logScale(
  domain: readonly [number, number],
  range: readonly [number, number],
): LinearScale {
  const low = Math.max(domain[0], 1e-4);
  const high = Math.max(domain[1], low * 10);
  const logLow = Math.log10(low);
  const logHigh = Math.log10(high);
  const [start, end] = range;

  const scale = ((value: number) => {
    const safe = Math.max(value, 1e-6);

    return start + ((Math.log10(safe) - logLow) / (logHigh - logLow)) * (end - start);
  }) as LinearScale;

  Object.defineProperty(scale, "domain", { value: [low, high] as const });
  Object.defineProperty(scale, "ticks", { value: () => decadeTicks(low, high) });

  return scale;
}

/**
 * Marcas de una escala logaritmica: 1, 2 y 5 por decada.
 *
 * Una marca por decada dejaria tres etiquetas en todo el eje; una por unidad
 * saturaria el extremo grueso. La serie 1-2-5 es el compromiso habitual.
 */
export function decadeTicks(low: number, high: number): number[] {
  const ticks: number[] = [];

  for (
    let exponent = Math.floor(Math.log10(low));
    exponent <= Math.ceil(Math.log10(high));
    exponent += 1
  ) {
    for (const multiple of [1, 2, 5]) {
      const value = multiple * 10 ** exponent;

      if (value >= low && value <= high) {
        ticks.push(value);
      }
    }
  }

  return ticks;
}

/** Extremos finitos de una o varias series, ignorando huecos. */
export function extentOf(...series: readonly (number | null)[][]): [number, number] {
  let low = Number.POSITIVE_INFINITY;
  let high = Number.NEGATIVE_INFINITY;

  for (const values of series) {
    for (const value of values) {
      if (value === null || !Number.isFinite(value)) {
        continue;
      }

      low = Math.min(low, value);
      high = Math.max(high, value);
    }
  }

  return Number.isFinite(low) ? [low, high] : [0, 1];
}

/** Ensancha un dominio por una fraccion de su amplitud. */
export function padExtent(extent: [number, number], fraction = 0.08): [number, number] {
  const [low, high] = extent;
  const pad = Math.max((high - low) * fraction, 1e-6);

  return [low - pad, high + pad];
}

/**
 * Marcas redondeadas dentro de un dominio.
 *
 * El paso se elige de la serie 1-2-5-10 para que las etiquetas caigan en
 * numeros que se leen de un vistazo.
 */
export function niceTicks(low: number, high: number, count: number): number[] {
  const raw = (high - low) / Math.max(count, 1);

  if (!Number.isFinite(raw) || raw <= 0) {
    return [low];
  }

  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const normalised = raw / magnitude;
  const step = (normalised <= 1 ? 1 : normalised <= 2 ? 2 : normalised <= 5 ? 5 : 10) * magnitude;
  const first = Math.ceil(low / step) * step;
  const ticks: number[] = [];

  for (let value = first; value <= high + step * 1e-6; value += step) {
    ticks.push(Math.abs(value) < step * 1e-6 ? 0 : value);
  }

  return ticks;
}

/**
 * Construye el atributo `d` de una polilinea, cortandola en los huecos.
 *
 * Un hueco es una medicion ausente, no un cero ni una interpolacion. Unir los
 * extremos de un hueco dibujaria una recta que el instrumento nunca midio, que
 * es exactamente el error que estos graficos existen para no cometer.
 */
export function linePath(
  values: readonly (number | null)[],
  x: (index: number) => number,
  y: (value: number) => number,
): string {
  const parts: string[] = [];
  let pen = "M";

  for (const [index, value] of values.entries()) {
    if (value === null || !Number.isFinite(value)) {
      pen = "M";
      continue;
    }

    parts.push(`${pen}${x(index).toFixed(1)} ${y(value).toFixed(1)}`);
    pen = "L";
  }

  return parts.join(" ");
}

/** Formatea un numero para una etiqueta de eje, sin decimales superfluos. */
export function axisLabel(value: number): string {
  const magnitude = Math.abs(value);
  const decimals = magnitude >= 100 ? 0 : magnitude >= 10 ? 1 : 2;

  return value.toLocaleString("es-CL", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}
