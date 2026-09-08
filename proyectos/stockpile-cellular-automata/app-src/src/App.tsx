/**
 * Visor interactivo del acopio intermedio anonimizado.
 *
 * El protagonista es el acopio. Los tres planos ortogonales encabezan la pagina
 * para poder compararlos de un vistazo y la vista tridimensional orbitable ocupa
 * el ancho completo debajo. La documentacion del modelo queda al final,
 * disponible pero subordinada.
 *
 * El indice de dias se descarga una vez y los cuadros solo del rango en
 * pantalla, acotado a una semana.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

import type { ColourMapId } from "./colormaps";
import { colourMap, sample } from "./colormaps";
import { HeightReconciliation } from "./components/HeightReconciliation";
import { OrthogonalView } from "./components/OrthogonalViews";
import { Playback } from "./components/Playback";
import type { WeekOption } from "./components/Playback";
import { SizeReconciliation } from "./components/SizeReconciliation";
import { Stockpile3D } from "./components/Stockpile3D";
import type { FramesIndex, LoadedRange } from "./frames";
import { clampRange, loadIndex, loadRange } from "./frames";
import { formatNumber } from "./theme";
import type { SizeUnit } from "./units";
import { DEFAULT_SIZE_UNIT, SIZE_UNITS, formatSize } from "./units";

const FRAMES_BASE = "./frames";
const DEFAULT_FRAMES_PER_SECOND = 5;
const DEFAULT_EXAGGERATION = 1.6;
const COLOUR_MAP_ID: ColourMapId = "rdylgn";
const INITIAL_RANGE_DAYS = 14;
const INITIAL_START_OFFSET_DAYS = 30;

export function App(): JSX.Element {
  const [index, setIndex] = useState<FramesIndex | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadIndex(FRAMES_BASE)
      .then(setIndex)
      .catch((cause: Error) => setError(cause.message));
  }, []);

  if (error) {
    return (
      <main className="loading">
        <h1>No fue posible cargar el acopio</h1>
        <p>{error}</p>
      </main>
    );
  }

  if (!index) {
    return (
      <main className="loading">
        <h1>Cargando el indice de dias…</h1>
      </main>
    );
  }

  return <Viewer index={index} />;
}

function Viewer({ index }: { index: FramesIndex }): JSX.Element {
  const days = useMemo(() => index.days.map((day) => day.date), [index]);
  const initialStart = Math.min(INITIAL_START_OFFSET_DAYS, Math.max(0, days.length - 1));
  const [fromDay, setFromDay] = useState(days[initialStart] ?? "");
  const [toDay, setToDay] = useState(
    days[Math.min(initialStart + INITIAL_RANGE_DAYS - 1, days.length - 1)] ?? "",
  );
  const [range, setRange] = useState<LoadedRange | null>(null);
  const [loading, setLoading] = useState(true);
  const [rangeError, setRangeError] = useState<string | null>(null);

  const [frameIndex, setFrameIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [framesPerSecond, setFramesPerSecond] = useState(DEFAULT_FRAMES_PER_SECOND);
  const [exaggeration, setExaggeration] = useState(DEFAULT_EXAGGERATION);
  const [showFeeders, setShowFeeders] = useState(true);
  const [sizeUnit, setSizeUnit] = useState<SizeUnit>(DEFAULT_SIZE_UNIT);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setRangeError(null);

    loadRange(FRAMES_BASE, index, fromDay, toDay)
      .then((loaded) => {
        if (cancelled) {
          return;
        }

        setRange(loaded);
        setFrameIndex(0);
      })
      .catch((cause: Error) => {
        if (!cancelled) {
          setRangeError(cause.message);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [index, fromDay, toDay]);

  const frameCount = range?.frames.length ?? 0;

  /*
   * La animacion recorre el periodo una vez y se detiene en el ultimo cuadro.
   *
   * Antes volvia al principio indefinidamente con un modulo. Un acopio en bucle
   * confunde: la transicion del ultimo cuadro al primero es un salto de varios
   * dias que se lee como un cambio brusco del acopio, y sin final no hay forma
   * de saber que se vio el periodo completo.
   */
  useEffect(() => {
    if (!playing || frameCount === 0) {
      return;
    }

    const timer = window.setInterval(() => {
      setFrameIndex((current) => {
        if (current >= frameCount - 1) {
          setPlaying(false);

          return frameCount - 1;
        }

        return current + 1;
      });
    }, 1000 / framesPerSecond);

    return () => window.clearInterval(timer);
  }, [playing, framesPerSecond, frameCount]);

  /*
   * Pulsar reproducir con la animacion terminada la reinicia desde el principio
   * en lugar de quedarse clavada en el ultimo cuadro sin avanzar.
   */
  const togglePlay = useCallback(() => {
    setPlaying((current) => {
      if (!current && frameIndex >= frameCount - 1) {
        setFrameIndex(0);
      }

      return !current;
    });
  }, [frameIndex, frameCount]);

  const handleFromDay = useCallback(
    (day: string) => {
      setPlaying(false);
      setFromDay(day);
      setToDay((current) => clampRange(index, day, current < day ? day : current));
    },
    [index],
  );

  const handleToDay = useCallback(
    (day: string) => {
      setPlaying(false);
      setToDay(clampRange(index, fromDay, day));
    },
    [index, fromDay],
  );

  const handleWeek = useCallback(
    (week: WeekOption) => {
      setPlaying(false);
      setFromDay(week.fromDay);
      setToDay(week.toDay);
    },
    [],
  );

  const frame = range?.frames[Math.min(frameIndex, frameCount - 1)];
  const [minSize, maxSize] = index.sizeRangeIn;
  const activeFrame = Math.min(frameIndex, Math.max(frameCount - 1, 0));
  const activeTimestamp = range?.timestamps[activeFrame] ?? "—";
  const activeApex = range?.apexHeightM[activeFrame];
  const activeInventory = range?.inventoryKt[activeFrame];

  return (
    <div className="app-shell">
      <header className="command-header">
        <div className="command-header-inner">
          <div className="product-lockup">
            <img className="brand-logo" src="./nerdyminer-icon.svg" alt="NerdyMiner" />
            <div>
              <span className="eyebrow">Digital Twin Lab – Edición pública</span>
              <h1>Modelo de stockpile 3D</h1>
              <p>Autómata celular 3D – Operación industrial transformada</p>
            </div>
          </div>
          <div className="status-cluster" aria-label="Estado del visor">
            <span><i className="status-dot" />Sistema disponible</span>
            <span>15 min / cuadro</span>
            <span>{index.days.length} días</span>
          </div>
        </div>
      </header>

      <main className="studio-main">
        <section className="intro-band">
          <div>
            <span className="eyebrow">Una ventana al interior</span>
            <h2>Forma, memoria y granulometría en movimiento</h2>
          </div>
          <p>
            El color representa tamaño medio; la geometría, el estado de llenado. Recorre una
            detención prolongada, el vaciado de la carga viva y la recuperación posterior sin
            perder la estructura interna que un instrumento superficial no observa.
          </p>
        </section>

        {rangeError ? <p className="range-error">{rangeError}</p> : null}
        {range && range.discardedKt > 0.5 ? (
          <p className="range-notice"><strong>{formatNumber(range.discardedKt, 1)} kt no modeladas</strong> en esta ventana para respetar la capacidad física de la grilla.</p>
        ) : null}
        {range && range.invalidDays.length > 0 ? (
          <p className="range-error"><strong>{range.invalidDays.length} días fuera del dominio físico.</strong> En ellos la superficie alcanza un límite de diseño o de grilla.</p>
        ) : null}

        <section className="workspace-grid">
          <div className="visual-workspace">
            <div className="panel-heading">
              <div><span className="eyebrow">Vista operacional</span><h2>Estado tridimensional</h2></div>
              <span className="live-time">{activeTimestamp}</span>
            </div>
            <section className="stage">
              {frame ? (
                <Stockpile3D index={index} frame={frame} width={1320} height={720}
                  verticalExaggeration={exaggeration} showFeeders={showFeeders}
                  colourMapId={COLOUR_MAP_ID} />
              ) : <Placeholder width={1320} height={720} loading={loading} />}
            </section>
            <div className="transport-dock">
              <Playback index={index} days={days} fromDay={fromDay} toDay={toDay}
                frameIndex={frameIndex} frameCount={frameCount} timestamps={range?.timestamps ?? []}
                apexHeightM={range?.apexHeightM ?? []} inventoryKt={range?.inventoryKt ?? []}
                playing={playing} loading={loading} framesPerSecond={framesPerSecond}
                onFromDayChange={handleFromDay} onToDayChange={handleToDay}
                onWeekChange={handleWeek} onFrameChange={setFrameIndex}
                onTogglePlay={togglePlay} onSpeedChange={setFramesPerSecond} />
            </div>
          </div>

          <aside className="control-rail">
            <section className="rail-card live-card">
              <span className="eyebrow">Estado actual</span>
              <div className="metric-grid">
                <Metric label="Altura ápice" value={activeApex?.toFixed(1) ?? "—"} unit="m" />
                <Metric label="Inventario" value={activeInventory?.toFixed(1) ?? "—"} unit="kt" />
                <Metric label="Cuadro" value={frameCount ? `${activeFrame + 1}` : "—"} unit={`/ ${frameCount}`} />
                <Metric label="Exageración" value={exaggeration.toFixed(1)} unit="×" />
              </div>
            </section>

            <section className="rail-card stage-options">
              <span className="eyebrow">Visualización</span>
          <label>
            Exageración vertical
            <input
              type="range"
              min={1}
              max={2}
              step={0.2}
              value={exaggeration}
              onChange={(event) => setExaggeration(Number(event.target.value))}
            />
            <span>{exaggeration.toFixed(1)}×</span>
          </label>

          <label className="checkbox toggle-row">
            <input
              type="checkbox"
              checked={showFeeders}
              onChange={(event) => setShowFeeders(event.target.checked)}
            />
            Mostrar infraestructura
          </label>

          <label>
            Unidad de tamaño
            <select
              value={sizeUnit}
              onChange={(event) => setSizeUnit(event.target.value as SizeUnit)}
            >
              {SIZE_UNITS.map((unit) => (
                <option key={unit.id} value={unit.id}>
                  {unit.label}
                </option>
              ))}
            </select>
          </label>

          <div className="legend">
            <span>fino {formatSize(minSize, sizeUnit)}</span>
            <div className="legend-ramp">
              {Array.from({ length: 40 }, (_, position) => (
                <span
                  key={position}
                  style={{ background: sample(colourMap(COLOUR_MAP_ID), position / 39) }}
                />
              ))}
            </div>
            <span>grueso {formatSize(maxSize, sizeUnit)}</span>
          </div>
            </section>

            <section className="rail-card spatial-key">
              <span className="eyebrow">Lectura espacial</span>
              <div className="key-row"><i className="key-line conveyor" /><span><strong>Correa de alimentación</strong><small>{index.conveyor?.inclinationDeg ?? 15}° de inclinación – Estructura fija, con descarga {(index.conveyor?.dischargeClearanceM ?? 1.32).toFixed(2)} m sobre la cota de diseño.</small></span></div>
              <div className="key-row"><i className="key-line feeders-a" /><span><strong>Alimentadores A</strong><small>Puntos de recuperación bajo la pila.</small></span></div>
              <div className="key-row"><i className="key-line feeders-b" /><span><strong>Alimentadores B</strong><small>Puntos de recuperación bajo la pila.</small></span></div>
              <p>No comparten cota ni función: la correa deposita desde arriba; los alimentadores extraen desde la base. Por eso no tienen que estar alineados.</p>
            </section>
          </aside>
        </section>

        <section className="diagnostic-section">
          <div className="section-heading"><span className="eyebrow">Tomografía del modelo</span><h2>Tres planos, una misma memoria interna</h2></div>
          <div className="planes">
            <ViewPanel title="Planta – X–Y" caption="Segregación y conos de extracción">
              {frame ? <OrthogonalView index={index} frame={frame} plane="plan" width={520} height={360} showFeeders={showFeeders} colourMapId={COLOUR_MAP_ID} /> : <Placeholder width={520} height={360} loading={loading} />}
            </ViewPanel>
            <ViewPanel title="Corte X–vertical" caption="Estratificación sobre el eje rotado">
              {frame ? <OrthogonalView index={index} frame={frame} plane="sectionEast" width={520} height={360} showFeeders={showFeeders} colourMapId={COLOUR_MAP_ID} /> : <Placeholder width={520} height={360} loading={loading} />}
            </ViewPanel>
            <ViewPanel title="Corte Y–vertical" caption="Zona viva sobre los alimentadores">
              {frame ? <OrthogonalView index={index} frame={frame} plane="sectionNorth" width={520} height={360} showFeeders={showFeeders} colourMapId={COLOUR_MAP_ID} /> : <Placeholder width={520} height={360} loading={loading} />}
            </ViewPanel>
          </div>
        </section>

        {range ? <section className="reconciliation-section">
          <div className="section-heading"><span className="eyebrow">Modelo contra instrumento</span><h2>Reconciliación operacional</h2></div>
          <div className="reconciliation-grid">
          <HeightReconciliation
            range={range}
            frameIndex={frameIndex}
            designHeightM={index.designHeightM ?? null}
            onFrameChange={setFrameIndex}
          />
          <SizeReconciliation range={range} sizeUnit={sizeUnit} />
          </div>
          {range.reconciliation === null ? (
            <p className="range-notice">
              Este export no incluye series de reconciliacion. Regenerar los cuadros con{" "}
              <code>uv run stockpile-frames</code> para obtenerlas.
            </p>
          ) : null}
        </section> : null}
      </main>
      <footer className="brand-footer"><strong>Digital Twin Lab – Demostración pedagógica</strong><span>{index.days.length} días disponibles</span><span>Escenario sintético – Equipos con nomenclatura ficticia</span></footer>
    </div>
  );
}

function Metric({ label, value, unit }: { label: string; value: string; unit: string }): JSX.Element {
  return <div className="metric"><span>{label}</span><strong>{value}<small>{unit}</small></strong></div>;
}

function ViewPanel({
  title,
  caption,
  children,
}: {
  title: string;
  caption: string;
  children: React.ReactNode;
}): JSX.Element {
  return (
    <figure className="view-panel">
      <figcaption>
        <strong>{title}</strong>
        <span>{caption}</span>
      </figcaption>
      {children}
    </figure>
  );
}

function Placeholder({
  width,
  height,
  loading,
}: {
  width: number;
  height: number;
  loading: boolean;
}): JSX.Element {
  return (
    <div className="placeholder" style={{ width: "100%", aspectRatio: `${width} / ${height}` }}>
      {loading ? "Descargando cuadros…" : "Sin datos para el rango"}
    </div>
  );
}

export default App;
