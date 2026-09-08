/**
 * Carga y decodificacion de los cuadros de simulacion.
 *
 * Los cuadros se sirven en un archivo binario por dia mas un indice que los
 * describe. El visor descarga el índice una vez y luego sólo los días del rango
 * en pantalla, acotado a dos semanas para mantener la interacción fluida.
 *
 * El binario llega cuantizado en enteros de 16 bits sin signo. Aqui solo se
 * describen vistas sobre ese buffer, sin copiarlo ni convertirlo a punto
 * flotante: la conversion se hace celda a celda en el momento de dibujar.
 */

/**
 * Maximo de dias que el visor carga y anima de una vez.
 *
 * Dos semanas. Cada día son unos 2,1 MB de cuadros que viven en memoria del
 * navegador mientras dure la animación; el límite evita descargas innecesarias.
 */
export const MAXIMUM_RANGE_DAYS = 14;

/**
 * Dias a partir de los cuales el visor advierte del peso de la descarga.
 *
 * Por debajo del tope, pero ya lo bastante pesado como para decir cuanto se va
 * a descargar antes de hacerlo.
 */
export const HEAVY_RANGE_DAYS = 10;

/** Peso aproximado de un dia de cuadros, en megabytes. */
export const MEGABYTES_PER_DAY = 2.1;

/** Geometria de la grilla de simulacion. */
export interface GridInfo {
  nEast: number;
  nNorth: number;
  nVertical: number;
  cellSizeM: number;
  /** Resolución vertical después del escalamiento público de alturas. */
  verticalCellSizeM?: number;
  centreEast: number;
  centreNorth: number;
}

/** Factores de cuantizacion declarados por el exportador. */
export interface Scales {
  height: number;
  size: number;
  fill: number;
}

/** Un alimentador y su posicion en la grilla. */
export interface FeederInfo {
  name: string;
  line: number;
  east: number;
  north: number;
  offsetM: number;
  /** Fraccion del tonelaje de su linea que tomo en la ventana simulada. */
  shareOfLine: number;
}

/** Procedencia de las entradas de la corrida.
 *
 * El reparto del tonelaje entre alimentadores puede venir de las velocidades
 * medidas o, si esos tags no estan, de un reparto uniforme entre los que
 * figuran en marcha. La diferencia cambia lo que el modelo puede afirmar, de
 * modo que se declara aqui en lugar de darse por supuesta en el texto.
 */
export interface InputProvenance {
  usedMeasuredFeederSpeeds: boolean;
  feedSizeReconstructedMinutes: number;
  minutesWithoutRunningFeeder: number;
  windowMinutes: number;
}

/** Entrada del indice para un dia.
 *
 * `valid` es falso cuando el acopio simulado supera la altura de diseno o
 * alcanza el borde de la grilla. En ese estado el flujo superficial queda
 * truncado y lo que se ve deja de representar al acopio: es consecuencia de que
 * el desbalance entre balanzas acumule material que el acopio no puede
 * contener.
 */
export interface DayEntry {
  date: string;
  file: string;
  frameCount: number;
  firstTimestamp: string;
  apexHeightM: number[];
  inventoryKt: number[];
  valid: boolean;
  exceedsDesignHeight: boolean;
  touchesGridEdge: boolean;
  /** Alimentacion que hubo que descartar para no exceder la capacidad, en kt. */
  discardedKt: number;
}

/** Indice que describe todos los dias disponibles. */
export interface FramesIndex {
  generatedAt: string;
  grid: GridInfo;
  scales: Scales;
  frameIntervalMinutes: number;
  angleOfReposeDeg: number;
  /**
   * Altura de diseno del acopio, en metros.
   *
   * Opcional para tolerar un export anterior a su incorporacion: sin ella el
   * grafico de reconciliacion omite la linea de referencia en lugar de fallar.
   */
  designHeightM?: number;
  feedGain: number;
  sizeRangeIn: [number, number];
  /** Rotación rígida aplicada a toda la geometría horizontal pública. */
  rotationDeg?: number;
  conveyor?: {
    bearingDeg: number;
    label: string;
    /** Inclinación de la correa respecto de la horizontal. */
    inclinationDeg?: number;
    /** Separación vertical del punto de descarga sobre la cota de diseño. */
    dischargeClearanceM?: number;
  };
  inputProvenance: InputProvenance;
  feeders: FeederInfo[];
  days: DayEntry[];
  /**
   * Verdadero cuando el export escribio un archivo de reconciliacion por dia.
   *
   * Es opcional para que un export anterior siga cargando: sin el, el visor
   * anima igual y solo omite los graficos de reconciliacion.
   */
  hasReconciliationSeries?: boolean;
}

/** Vistas sobre un cuadro, sin copiar el buffer subyacente. */
export interface Frame {
  /** Elevacion de la superficie por columna, cuantizada. */
  height: Uint16Array;
  /** Tamano medio por columna, cuantizado. */
  columnSize: Uint16Array;
  /** Tamano en el plano vertical Este-Vertical que pasa por el eje. */
  sectionEastSize: Uint16Array;
  /** Llenado en el mismo plano. */
  sectionEastFill: Uint16Array;
  /** Tamano en el plano vertical Norte-Vertical que pasa por el eje. */
  sectionNorthSize: Uint16Array;
  /** Llenado en el mismo plano. */
  sectionNorthFill: Uint16Array;
}

/** Deciles que publican las camaras Split. */
export const DECILES = [10, 20, 30, 40, 50, 60, 70, 80, 90] as const;

/**
 * Series de reconciliacion de un cuadro, emparejadas con lo medido en planta.
 *
 * Viven en un JSON por dia, aparte del binario, porque se comparan contra
 * mediciones y la cuantizacion a entero de 16 bits del binario perderia
 * resolucion justo donde importa.
 *
 * `unmodelledT` es el tonelaje que hubo que descartar para respetar la
 * capacidad del acopio: mineral que las balanzas dicen que entro y que el
 * acopio no puede contener. Es la parte del balance que el modelo NO explica.
 */
export interface ReconciliationSeries {
  simulatedHeightM: (number | null)[];
  measuredHeightM: (number | null)[];
  unmodelledT: (number | null)[];
  simulatedLine1P80In: (number | null)[];
  simulatedLine2P80In: (number | null)[];
  measuredLine1P80In: (number | null)[];
  measuredLine2P80In: (number | null)[];
  measuredFeedTopsizeIn: (number | null)[];
  measuredLine1TopsizeIn: (number | null)[];
  measuredLine2TopsizeIn: (number | null)[];
  [series: string]: (number | null)[];
}

/** Rango de dias ya descargado y listo para animar. */
export interface LoadedRange {
  fromDay: string;
  toDay: string;
  frames: Frame[];
  timestamps: string[];
  apexHeightM: number[];
  inventoryKt: number[];
  /** Dias del rango que no son fisicamente validos. */
  invalidDays: string[];
  /** Alimentacion descartada en el rango, en kt. */
  discardedKt: number;
  /** Series de reconciliacion concatenadas, o `null` si el export no las trae. */
  reconciliation: ReconciliationSeries | null;
}

/** Numero de enteros de 16 bits que ocupa cada cuadro. */
function frameLength(grid: GridInfo): number {
  return grid.nEast * grid.nNorth * 2 + grid.nEast * grid.nVertical * 2 + grid.nNorth * grid.nVertical * 2;
}

/**
 * Descompone el binario de un dia en vistas por cuadro.
 *
 * @throws Si el tamano no coincide con lo que declara el indice, lo que
 *   indicaria que el binario y el indice provienen de corridas distintas.
 */
export function decodeDay(buffer: ArrayBuffer, index: FramesIndex, day: DayEntry): Frame[] {
  const { nEast, nNorth, nVertical } = index.grid;
  const plan = nEast * nNorth;
  const sectionEast = nEast * nVertical;
  const sectionNorth = nNorth * nVertical;
  const perFrame = frameLength(index.grid);
  const expected = perFrame * day.frameCount * Uint16Array.BYTES_PER_ELEMENT;

  if (buffer.byteLength !== expected) {
    throw new Error(
      `${day.file} mide ${buffer.byteLength} bytes y el indice declara ${expected}: ` +
        "el binario y el indice provienen de corridas distintas, hay que regenerarlos juntos",
    );
  }

  const all = new Uint16Array(buffer);
  const frames: Frame[] = [];

  for (let position = 0; position < day.frameCount; position += 1) {
    let cursor = position * perFrame;
    const take = (length: number): Uint16Array => {
      const view = all.subarray(cursor, cursor + length);
      cursor += length;

      return view;
    };

    frames.push({
      height: take(plan),
      columnSize: take(plan),
      sectionEastSize: take(sectionEast),
      sectionEastFill: take(sectionEast),
      sectionNorthSize: take(sectionNorth),
      sectionNorthFill: take(sectionNorth),
    });
  }

  return frames;
}

/**
 * Descarga el indice de dias disponibles.
 *
 * @throws Si el indice no esta disponible, con la instruccion para generarlo.
 */
export async function loadIndex(base = "./frames"): Promise<FramesIndex> {
  const response = await fetch(`${base}/index.json`);

  if (!response.ok) {
    throw new Error(
      "no se encontro el indice de cuadros. Generarlo con `uv run stockpile-frames` " +
        "y servir la aplicacion con `npm run preview`: abrir el archivo directamente " +
        "desde el disco no permite leer datos binarios.",
    );
  }

  return (await response.json()) as FramesIndex;
}

/** Marcas de tiempo de un dia, derivadas de su primera y del intervalo. */
function timestampsOf(index: FramesIndex, day: DayEntry): string[] {
  const first = new Date(`${day.firstTimestamp.replace(" ", "T")}Z`);

  return Array.from({ length: day.frameCount }, (_, position) => {
    const moment = new Date(
      first.getTime() + position * index.frameIntervalMinutes * 60_000,
    );

    return moment.toISOString().slice(0, 16).replace("T", " ");
  });
}

/**
 * Descarga y decodifica los dias comprendidos entre dos fechas.
 *
 * @param base Prefijo de ruta donde viven el indice y los binarios.
 * @param index Indice ya descargado.
 * @param fromDay Primer dia del rango.
 * @param toDay Ultimo dia del rango.
 * @returns Cuadros concatenados y sus series de apoyo.
 * @throws Si el rango no contiene ningun dia o excede
 *   {@link MAXIMUM_RANGE_DAYS}.
 */
export async function loadRange(
  base: string,
  index: FramesIndex,
  fromDay: string,
  toDay: string,
): Promise<LoadedRange> {
  const selected = index.days.filter((day) => day.date >= fromDay && day.date <= toDay);

  if (selected.length === 0) {
    throw new Error(`no hay dias disponibles entre ${fromDay} y ${toDay}`);
  }

  /*
   * El tope se comprueba aqui y no solo en el selector: la funcion es publica y
   * un rango pedido por programa cargaria cientos de megabytes sin que nada lo
   * impidiera. Fallar es preferible a colgar la pestana.
   */
  if (selected.length > MAXIMUM_RANGE_DAYS) {
    throw new Error(
      `el rango abarca ${selected.length} dias y el maximo es ${MAXIMUM_RANGE_DAYS}`,
    );
  }

  const buffers = await Promise.all(
    selected.map(async (day) => {
      const response = await fetch(`${base}/${day.file}`);

      if (!response.ok) {
        throw new Error(`no se pudo descargar ${day.file}`);
      }

      return response.arrayBuffer();
    }),
  );

  const seriesByDay = await Promise.all(
    selected.map((day) => loadDaySeries(base, day, index.hasReconciliationSeries === true)),
  );

  const frames: Frame[] = [];
  const timestamps: string[] = [];
  const apexHeightM: number[] = [];
  const inventoryKt: number[] = [];

  for (const [position, day] of selected.entries()) {
    frames.push(...decodeDay(buffers[position]!, index, day));
    timestamps.push(...timestampsOf(index, day));
    apexHeightM.push(...day.apexHeightM);
    inventoryKt.push(...day.inventoryKt);
  }

  return {
    fromDay: selected[0]!.date,
    toDay: selected[selected.length - 1]!.date,
    frames,
    timestamps,
    apexHeightM,
    inventoryKt,
    invalidDays: selected.filter((day) => !day.valid).map((day) => day.date),
    discardedKt: selected.reduce((total, day) => total + day.discardedKt, 0),
    reconciliation: concatenateSeries(seriesByDay),
  };
}

/**
 * Descarga las series de reconciliacion de un dia.
 *
 * Devuelve `null` en lugar de fallar cuando el export no las trae: un export
 * anterior sigue siendo animable, solo pierde los graficos de reconciliacion.
 */
async function loadDaySeries(
  base: string,
  day: DayEntry,
  expected: boolean,
): Promise<ReconciliationSeries | null> {
  if (!expected) {
    return null;
  }

  const response = await fetch(`${base}/${day.date}.series.json`);

  if (!response.ok) {
    return null;
  }

  const payload = (await response.json()) as { series: ReconciliationSeries };

  return payload.series;
}

/**
 * Concatena las series de varios dias en una sola.
 *
 * Si algun dia del rango no trae series, se descarta el conjunto: una serie con
 * un dia faltante silenciosamente omitido quedaria desalineada con la linea de
 * tiempo de la animacion y compararia cuadros con instantes que no les
 * corresponden.
 */
function concatenateSeries(
  days: (ReconciliationSeries | null)[],
): ReconciliationSeries | null {
  if (days.length === 0 || days.some((day) => day === null)) {
    return null;
  }

  const present = days as ReconciliationSeries[];
  const merged: Record<string, (number | null)[]> = {};

  for (const name of Object.keys(present[0]!)) {
    merged[name] = present.flatMap((day) => day[name] ?? []);
  }

  return merged as ReconciliationSeries;
}

/**
 * Acota un rango de dias al maximo admitido, moviendo el extremo final.
 *
 * @returns El ultimo dia admisible para el primero dado.
 */
export function clampRange(index: FramesIndex, fromDay: string, toDay: string): string {
  const available = index.days.map((day) => day.date);
  const start = available.indexOf(fromDay);

  if (start < 0) {
    return fromDay;
  }

  if (toDay < fromDay) {
    return fromDay;
  }

  const limit = available[Math.min(start + MAXIMUM_RANGE_DAYS - 1, available.length - 1)]!;

  return toDay > limit ? limit : toDay;
}
