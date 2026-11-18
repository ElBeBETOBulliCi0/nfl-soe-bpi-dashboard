import { useMemo, useState } from 'react';
import type { BpiDownDistanceCell } from '../api/types';
import { bpiColor, buildDxd, DXD_COLUMNS, DXD_DOWNS } from '../lib/bpi';
import type { DxdCell } from '../lib/bpi';
import { fmtBpi, fmtPct, fmtYards } from '../lib/format';

export interface DxdMatrixProps {
  /** `down_distance` array of /api/bpi/summary (requested without down and distance filters). */
  cells: BpiDownDistanceCell[];
}

const NEUTRAL_BG = 'rgb(30, 41, 59)'; // slate-800
const POSITIVE_RGB = '59, 130, 246'; // blue
const NEGATIVE_RGB = '239, 68, 68'; // red

function cellBackground(bpi: number | null, maxAbs: number): string {
  const c = bpiColor(bpi, maxAbs);
  if (!c || c.hue === 'neutral') return NEUTRAL_BG;
  const alpha = 0.15 + 0.85 * c.intensity;
  return `rgba(${c.hue === 'positive' ? POSITIVE_RGB : NEGATIVE_RGB}, ${alpha.toFixed(3)})`;
}

interface Active {
  down: number;
  distanceLabel: string;
  cell: DxdCell | null;
}

export function DxdMatrix({ cells }: DxdMatrixProps) {
  const [active, setActive] = useState<Active | null>(null);
  const { rows, maxAbs } = useMemo(() => buildDxd(cells), [cells]);

  return (
    <section aria-label="Matriz BPI por down y distancia" className="rounded-lg border border-slate-700 bg-slate-900 p-4">
      <h2 className="mb-1 text-lg font-semibold text-slate-100">BPI por down y distancia</h2>
      <p className="mb-3 text-sm text-slate-300">
        Azul: BPI positivo, la presión compensa las yardas permitidas. Rojo: BPI negativo, el blitz salió caro.
      </p>

      <div
        role="tooltip"
        aria-live="polite"
        className="mb-3 min-h-[3.5rem] rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"
      >
        {active ? (
          <dl className="grid grid-cols-2 gap-x-4 gap-y-0.5 sm:grid-cols-6">
            <div>
              <dt className="text-xs text-slate-300">Down</dt>
              <dd>{active.down}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-300">Distancia</dt>
              <dd>{active.distanceLabel}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-300">BPI</dt>
              <dd>{fmtBpi(active.cell?.bpi)}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-300">Tasa de presión</dt>
              <dd>{fmtPct(active.cell?.pressure_rate)}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-300">Yardas permitidas</dt>
              <dd>{fmtYards(active.cell?.mean_yards_allowed)}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-300">Jugadas</dt>
              <dd>{active.cell?.n_plays ?? 0}</dd>
            </div>
          </dl>
        ) : (
          <span className="text-slate-300">Pasa el cursor o enfoca una celda para ver el detalle.</span>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="border-separate border-spacing-1 text-sm">
          <thead>
            <tr>
              <th className="px-2 py-1 text-left text-xs font-medium text-slate-300">Down \ Distancia</th>
              {DXD_COLUMNS.map((col) => (
                <th key={col.bucket} scope="col" className="px-2 py-1 text-center text-xs font-medium text-slate-300">
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {DXD_DOWNS.map((down, i) => (
              <tr key={down}>
                <th scope="row" className="whitespace-nowrap px-2 py-1 text-left text-xs font-medium text-slate-200">
                  Down {down}
                </th>
                {DXD_COLUMNS.map((col, j) => {
                  const cell = rows[i][j];
                  const label = `Down ${down}, ${col.label}`;
                  return (
                    <td key={col.bucket} className="p-0">
                      <button
                        type="button"
                        onMouseEnter={() => setActive({ down, distanceLabel: col.label, cell })}
                        onMouseLeave={() => setActive(null)}
                        onFocus={() => setActive({ down, distanceLabel: col.label, cell })}
                        onBlur={() => setActive(null)}
                        aria-label={
                          cell
                            ? `${label}: BPI ${fmtBpi(cell.bpi)}, tasa de presión ${fmtPct(
                                cell.pressure_rate,
                              )}, yardas permitidas ${fmtYards(cell.mean_yards_allowed)}, ${cell.n_plays} jugadas`
                            : `${label}: sin datos`
                        }
                        style={{ backgroundColor: cell ? cellBackground(cell.bpi, maxAbs) : NEUTRAL_BG }}
                        className="h-12 w-full min-w-[4.5rem] rounded px-1 text-xs font-semibold text-white focus:outline-none focus:ring-2 focus:ring-white"
                      >
                        {cell ? fmtBpi(cell.bpi) : '—'}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-slate-200" aria-label="Leyenda de color">
        <span>{maxAbs > 0 ? `−${maxAbs.toFixed(2)}` : '−'}</span>
        <div
          className="h-3 w-48 rounded"
          style={{
            background: `linear-gradient(to right, rgba(${NEGATIVE_RGB}, 1), ${NEUTRAL_BG}, rgba(${POSITIVE_RGB}, 1))`,
          }}
        />
        <span>{maxAbs > 0 ? `+${maxAbs.toFixed(2)}` : '+'}</span>
        <span className="text-slate-300">Centro: 0 (la presión iguala las yardas permitidas)</span>
      </div>
    </section>
  );
}

export default DxdMatrix;
