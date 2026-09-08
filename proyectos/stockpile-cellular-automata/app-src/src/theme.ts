/**
 * Paleta y escalas del reporte.
 *
 * Paleta generica de alto contraste. El mensaje analitico manda sobre la marca:
 * cuando una distincion es critica no se confia
 * solo en el color, y las escalas secuenciales se ordenan por luminosidad para
 * seguir siendo legibles sin percepcion de color.
 */

export const palette = {
  darkTeal: "#1C434B",
  dodgerBlue: "#007ED3",
  navy: "#002060",
  teal: "#205762",
  orange: "#E97132",
  salmon: "#D37154",
  graphite: "#434444",
  goldenrod: "#E8B22C",
} as const;

export const semantic = {
  /** Linea 1 de molienda. */
  line1: palette.dodgerBlue,
  /** Linea 2 de molienda, la que recibe mineral mas grueso. */
  line2: palette.orange,
  /** Valor medido dentro del escenario pedagógico. */
  measured: palette.graphite,
  /** Valor simulado por el modelo. */
  simulated: palette.dodgerBlue,
  /** Condicion que degrada el resultado. */
  warning: palette.goldenrod,
  /** Hallazgo que exige accion. */
  alert: palette.salmon,
  /** Confirmacion o cierre correcto. */
  good: palette.teal,
} as const;

/**
 * Escala secuencial para el tamano de particula, de fino a grueso.
 *
 * Va de azul frio a naranja calido pasando por un amarillo intermedio, de modo
 * que el orden se percibe tambien como progresion de luminosidad.
 */
const sizeRamp: readonly [number, number, number][] = [
  [0x1c, 0x43, 0x4b],
  [0x20, 0x57, 0x62],
  [0x00, 0x7e, 0xd3],
  [0xe8, 0xb2, 0x2c],
  [0xe9, 0x71, 0x32],
  [0xd3, 0x71, 0x54],
];

/**
 * Interpola la escala de tamano.
 *
 * @param fraction Posicion en la escala, acotada a `[0, 1]`.
 * @returns Color CSS.
 */
export function sizeColour(fraction: number): string {
  if (!Number.isFinite(fraction)) {
    return "#2a2a2a";
  }

  const clamped = Math.min(1, Math.max(0, fraction));
  const scaled = clamped * (sizeRamp.length - 1);
  const lower = Math.floor(scaled);
  const upper = Math.min(sizeRamp.length - 1, lower + 1);
  const weight = scaled - lower;
  const start = sizeRamp[lower] ?? sizeRamp[0]!;
  const end = sizeRamp[upper] ?? sizeRamp[sizeRamp.length - 1]!;
  const mix = (index: number): number =>
    Math.round((start[index] ?? 0) * (1 - weight) + (end[index] ?? 0) * weight);

  return `rgb(${mix(0)}, ${mix(1)}, ${mix(2)})`;
}

/** Formatea un numero con separador de miles y decimales fijos. */
export function formatNumber(value: number, decimals = 0): string {
  return value.toLocaleString("es-CL", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/** Formatea un valor con signo explicito, util para diferencias y sesgos. */
export function formatSigned(value: number, decimals = 2): string {
  const sign = value >= 0 ? "+" : "";

  return `${sign}${formatNumber(value, decimals)}`;
}
