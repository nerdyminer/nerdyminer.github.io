/**
 * Unidad de tamano de particula del visor.
 *
 * Las camaras Split publican en pulgadas y todo el modelo trabaja en pulgadas,
 * de modo que la pulgada es la unidad interna y la conversion ocurre solo al
 * dibujar. Convertir antes obligaria a arrastrar la unidad por el nucleo, la
 * reconciliacion y el archivo de series, donde no aporta nada y multiplica las
 * ocasiones de mezclar escalas.
 *
 * La operacion razona en pulgadas por costumbre de la camara, pero la
 * metalurgia y los reportes corporativos usan milimetros, asi que la eleccion
 * es del lector.
 */

export type SizeUnit = "in" | "mm";

export const MILLIMETRES_PER_INCH = 25.4;

export const SIZE_UNITS: readonly { id: SizeUnit; label: string }[] = [
  { id: "in", label: "Pulgadas" },
  { id: "mm", label: "Milimetros" },
] as const;

export const DEFAULT_SIZE_UNIT: SizeUnit = "in";

/** Convierte pulgadas a la unidad de presentacion. */
export function toUnit(inches: number, unit: SizeUnit): number {
  return unit === "mm" ? inches * MILLIMETRES_PER_INCH : inches;
}

/** Sufijo de la unidad, con la comilla doble para la pulgada. */
export function unitSuffix(unit: SizeUnit): string {
  return unit === "mm" ? " mm" : "″";
}

/**
 * Formatea un tamano en la unidad elegida.
 *
 * Los decimales se eligen por magnitud y no de forma fija: en pulgadas un P80
 * de 4.23 necesita dos decimales para distinguirse de 4.30, mientras que los
 * mismos valores en milimetros son 107 y 109, donde un decimal ya es ruido.
 *
 * @param inches Valor en pulgadas, la unidad interna.
 * @param unit Unidad de presentacion.
 * @param decimals Decimales explicitos; si se omite se eligen por magnitud.
 */
export function formatSize(inches: number, unit: SizeUnit, decimals?: number): string {
  if (!Number.isFinite(inches)) {
    return "n/d";
  }

  const value = toUnit(inches, unit);
  const places = decimals ?? (Math.abs(value) >= 100 ? 0 : Math.abs(value) >= 10 ? 1 : 2);
  const text = value.toLocaleString("es-CL", {
    minimumFractionDigits: places,
    maximumFractionDigits: places,
  });

  return `${text}${unitSuffix(unit)}`;
}

/**
 * Formatea una marca de eje, sin sufijo y sin decimales superfluos.
 *
 * El valor ya viene en la unidad de presentacion: las marcas de una escala
 * logaritmica se calculan sobre el dominio convertido para que caigan en
 * numeros redondos de esa unidad, no en las pulgadas traducidas.
 */
export function formatTick(value: number): string {
  if (value >= 1) {
    return value.toLocaleString("es-CL", { maximumFractionDigits: 0 });
  }

  return value.toLocaleString("es-CL", { maximumFractionDigits: 2 });
}
