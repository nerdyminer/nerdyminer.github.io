/**
 * Controles de reproduccion de la animacion.
 *
 * El rango se elige con granularidad diaria porque es la unidad con que se
 * razona la operacion del acopio, mientras que la animacion avanza en cuadros de
 * quince minutos, que es la escala a la que el acopio cambia de forma
 * apreciable.
 *
 * El rango está acotado a catorce días. Cada día son 96 cuadros y unos 2 MB que
 * viven en memoria del navegador mientras dure la animación. El límite mantiene
 * una experiencia fluida y coincide con la ventana pedagógica del proyecto.
 *
 * La velocidad se expresa en cuadros por segundo y no en un multiplicador de
 * tiempo real: a quince minutos por cuadro, incluso la velocidad mas lenta
 * equivale a acelerar la operacion novecientas veces, de modo que un
 * multiplicador no significaria nada util.
 */

import { useMemo } from "react";

import { HEAVY_RANGE_DAYS, MAXIMUM_RANGE_DAYS, MEGABYTES_PER_DAY } from "../frames";
import type { FramesIndex } from "../frames";

export const SPEED_OPTIONS = [
  { label: "Muy lenta", framesPerSecond: 1 },
  { label: "Lenta", framesPerSecond: 2 },
  { label: "Normal", framesPerSecond: 5 },
  { label: "Rapida", framesPerSecond: 12 },
  { label: "Muy rapida", framesPerSecond: 24 },
] as const;

/**
 * Semanas completas disponibles, para el selector rapido.
 *
 * La semana es la unidad natural de revision de la operacion y cabe holgada
 * dentro del tope de dos semanas, de modo que un solo clic deja una ventana cómoda
 * de animar. Se agrupa por semana ISO, de lunes a domingo.
 */
export interface WeekOption {
  /** Etiqueta legible, con el numero de semana y el rango de fechas. */
  label: string;
  fromDay: string;
  toDay: string;
}

export function weekOptions(days: string[]): WeekOption[] {
  const byWeek = new Map<string, string[]>();

  for (const day of days) {
    const key = isoWeekKey(day);
    byWeek.set(key, [...(byWeek.get(key) ?? []), day]);
  }

  return [...byWeek.entries()]
    .map(([key, members]) => {
      const sorted = [...members].sort();
      const first = sorted[0]!;
      const last = sorted[sorted.length - 1]!;

      return {
        label: `${key} – ${first.slice(5)} a ${last.slice(5)} (${sorted.length} d)`,
        fromDay: first,
        toDay: last,
      };
    })
    .sort((left, right) => left.fromDay.localeCompare(right.fromDay));
}

/**
 * Clave de semana ISO 8601, con el ano al que pertenece la semana.
 *
 * El ano ISO no siempre coincide con el del calendario: el 1 de enero puede caer
 * en la ultima semana del ano anterior. Usar el ano del calendario mezclaria en
 * una misma clave dias de dos anos distintos.
 */
function isoWeekKey(day: string): string {
  const date = new Date(`${day}T00:00:00Z`);
  const weekday = (date.getUTCDay() + 6) % 7;
  date.setUTCDate(date.getUTCDate() - weekday + 3);
  const isoYear = date.getUTCFullYear();
  const firstThursday = new Date(Date.UTC(isoYear, 0, 4));
  const firstWeekday = (firstThursday.getUTCDay() + 6) % 7;
  firstThursday.setUTCDate(firstThursday.getUTCDate() - firstWeekday + 3);
  const week = 1 + Math.round((date.getTime() - firstThursday.getTime()) / (7 * 86_400_000));

  return `${isoYear}-S${String(week).padStart(2, "0")}`;
}

interface PlaybackProps {
  index: FramesIndex;
  days: string[];
  fromDay: string;
  toDay: string;
  frameIndex: number;
  frameCount: number;
  timestamps: string[];
  apexHeightM: number[];
  inventoryKt: number[];
  playing: boolean;
  loading: boolean;
  framesPerSecond: number;
  onFromDayChange: (day: string) => void;
  onToDayChange: (day: string) => void;
  onWeekChange: (week: WeekOption) => void;
  onFrameChange: (position: number) => void;
  onTogglePlay: () => void;
  onSpeedChange: (framesPerSecond: number) => void;
}

export function Playback({
  index,
  days,
  fromDay,
  toDay,
  frameIndex,
  frameCount,
  timestamps,
  apexHeightM,
  inventoryKt,
  playing,
  loading,
  framesPerSecond,
  onFromDayChange,
  onToDayChange,
  onWeekChange,
  onFrameChange,
  onTogglePlay,
  onSpeedChange,
}: PlaybackProps): JSX.Element {
  const spanHours = (frameCount * index.frameIntervalMinutes) / 60;
  const spanDays = countDaysBetween(days, fromDay, toDay);
  const latestAllowed = latestDayWithin(days, fromDay);
  const weeks = useMemo(() => weekOptions(days), [days]);
  // La semana activa es la que arranca en el dia inicial elegido; si el rango se
  // ajusto a mano, ninguna coincide y el selector queda en blanco a proposito.
  const activeWeek = weeks.find((week) => week.fromDay === fromDay && week.toDay === toDay);

  return (
    <div className="playback">
      <div className="playback-row">
        <label>
          Desde
          <select
            value={fromDay}
            disabled={loading}
            onChange={(event) => onFromDayChange(event.target.value)}
          >
            {days.map((day) => (
              <option key={day} value={day}>
                {day}
              </option>
            ))}
          </select>
        </label>

        <label>
          Hasta
          <select
            value={toDay}
            disabled={loading}
            onChange={(event) => onToDayChange(event.target.value)}
          >
            {days.map((day) => (
              <option key={day} value={day} disabled={day < fromDay || day > latestAllowed}>
                {day}
              </option>
            ))}
          </select>
        </label>

        <label>
          Semana
          <select
            value={activeWeek ? activeWeek.fromDay : ""}
            disabled={loading}
            onChange={(event) => {
              const chosen = weeks.find((week) => week.fromDay === event.target.value);

              if (chosen) {
                onWeekChange(chosen);
              }
            }}
          >
            <option value="">Rango a medida</option>
            {weeks.map((week) => (
              <option key={week.fromDay} value={week.fromDay}>
                {week.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          Velocidad
          <select
            value={framesPerSecond}
            onChange={(event) => onSpeedChange(Number(event.target.value))}
          >
            {SPEED_OPTIONS.map((option) => (
              <option key={option.label} value={option.framesPerSecond}>
                {option.label} – {option.framesPerSecond} cuadros/s
              </option>
            ))}
          </select>
        </label>

        <button type="button" className="play" onClick={onTogglePlay} disabled={loading}>
          {playing ? "Pausar" : "Reproducir"}
        </button>
      </div>

      <div className="playback-row">
        <input
          type="range"
          min={0}
          max={Math.max(frameCount - 1, 0)}
          value={Math.min(frameIndex, Math.max(frameCount - 1, 0))}
          disabled={loading || frameCount === 0}
          onChange={(event) => onFrameChange(Number(event.target.value))}
        />
        <span className="stamp">{timestamps[frameIndex] ?? "—"}</span>
      </div>

      <p className="playback-note">
        {frameCount} cuadros de {index.frameIntervalMinutes} min ({spanHours.toFixed(0)} h de
        operación). Ápice {apexHeightM[frameIndex]?.toFixed(1) ?? "—"} m – Inventario{" "}
        {inventoryKt[frameIndex]?.toFixed(1) ?? "—"} kt
      </p>

      {spanDays >= HEAVY_RANGE_DAYS ? (
        <p className="playback-warning">
          {spanDays} dias son unos {Math.round(spanDays * MEGABYTES_PER_DAY)} MB de cuadros que el
          navegador mantiene en memoria durante la animacion. La descarga puede tardar.
          {toDay === latestAllowed && latestAllowed < days[days.length - 1]!
            ? ` El maximo es ${MAXIMUM_RANGE_DAYS} dias: para avanzar en el tiempo, mover el dia inicial.`
            : ""}
        </p>
      ) : null}
    </div>
  );
}

/** Dias exportados comprendidos en el rango, ambos extremos incluidos. */
function countDaysBetween(days: string[], fromDay: string, toDay: string): number {
  return days.filter((day) => day >= fromDay && day <= toDay).length;
}

/** Ultimo dia seleccionable respetando el tope de un mes. */
function latestDayWithin(days: string[], fromDay: string): string {
  const start = days.indexOf(fromDay);

  if (start < 0) {
    return days[days.length - 1] ?? fromDay;
  }

  return days[Math.min(start + MAXIMUM_RANGE_DAYS - 1, days.length - 1)] ?? fromDay;
}
