/**
 * Escalas de color para la granulometria.
 *
 * La escala del acopio no es decorativa: codifica tamaño de partícula. La
 * edición pública fija `RdYlGn` para que todos los cuadros mantengan la misma
 * semántica operacional: verde fino, amarillo intermedio y rojo grueso.
 */

export type ColourMapId = "rdylgn";

export interface ColourMap {
  id: ColourMapId;
  label: string;
  /** Verdadero cuando la escala es divergente y no secuencial. */
  diverging: boolean;
  /** Nota breve para la leyenda. */
  note: string;
  stops: readonly (readonly [number, number, number])[];
}

/*
 * Los puntos de control se listan de FINO a GRUESO. RdYlGn se declara ya
 * invertida respecto de matplotlib, porque alli el extremo verde es el alto y
 * aqui lo deseable es el material fino.
 */
export const COLOUR_MAPS: readonly ColourMap[] = [
  {
    id: "rdylgn",
    label: "RdYlGn (verde fino, rojo grueso)",
    diverging: true,
    note: "divergente: exagera el contraste en torno al centro de la escala",
    stops: [
      [0x00, 0x64, 0x37],
      [0x1a, 0x96, 0x41],
      [0x86, 0xcb, 0x66],
      [0xd9, 0xef, 0x8b],
      [0xff, 0xff, 0xbf],
      [0xfe, 0xe0, 0x8b],
      [0xfd, 0xae, 0x61],
      [0xf4, 0x6d, 0x43],
      [0xa5, 0x00, 0x26],
    ],
  },
] as const;

export const DEFAULT_COLOUR_MAP: ColourMapId = "rdylgn";

const BY_ID = new Map<ColourMapId, ColourMap>(COLOUR_MAPS.map((map) => [map.id, map]));

/** Devuelve la escala pedida, cayendo en la secuencial base si el identificador no existe. */
export function colourMap(id: ColourMapId): ColourMap {
  return BY_ID.get(id) ?? BY_ID.get(DEFAULT_COLOUR_MAP)!;
}

/**
 * Interpola una escala.
 *
 * @param map Escala a muestrear.
 * @param fraction Posicion en la escala, acotada a `[0, 1]`.
 * @returns Color CSS. Los valores no finitos devuelven un gris neutro, que en el
 *   acopio significa celda sin dato y no un tamano intermedio.
 */
export function sample(map: ColourMap, fraction: number): string {
  if (!Number.isFinite(fraction)) {
    return "#2a2a2a";
  }

  const stops = map.stops;
  const clamped = Math.min(1, Math.max(0, fraction));
  const scaled = clamped * (stops.length - 1);
  const lower = Math.floor(scaled);
  const upper = Math.min(stops.length - 1, lower + 1);
  const weight = scaled - lower;
  const start = stops[lower] ?? stops[0]!;
  const end = stops[upper] ?? stops[stops.length - 1]!;
  const mix = (channel: number): number =>
    Math.round((start[channel] ?? 0) * (1 - weight) + (end[channel] ?? 0) * weight);

  return `rgb(${mix(0)}, ${mix(1)}, ${mix(2)})`;
}

/**
 * Construye una funcion de color ya ligada a una escala.
 *
 * Se pasa a los componentes de dibujo en lugar del identificador para que no
 * tengan que resolver la escala en cada celda: una vista en planta hace dos mil
 * seiscientas llamadas por cuadro.
 */
export function colourScale(id: ColourMapId): (fraction: number) => string {
  const map = colourMap(id);

  return (fraction: number) => sample(map, fraction);
}
