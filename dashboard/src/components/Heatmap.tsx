import { useMemo, useState } from 'react';
import type { HeatmapCell } from '../api/types';
import { fmtYards } from '../lib/format';

export interface HeatmapProps {
  cells: HeatmapCell[];
}

const NEUTRAL_BG = 'rgb(30, 41, 59)'; // slate-800
const POSITIVE_RGB = '59, 130, 246'; // blue
const NEGATIVE_RGB = '239, 68, 68'; // red

/** Diverging scale centered on 0: blue for positive, red for negative; intensity grows with |v|. */
function cellColor(v: number | null, maxAbs: number): string {
  if (v == null || v === 0 || maxAbs <= 0) return NEUTRAL_BG;
  const intensity = Math.min(1, Math.abs(v) / maxAbs);
  const alpha = 0.15 + 0.85 * intensity;
  return `rgba(${v > 0 ? POSITIVE_RGB : NEGATIVE_RGB}, ${alpha.toFixed(3)})`;
}

const lbl = (s: string | null) => s ?? '—';

export function Heatmap({ cells }: HeatmapProps) {
  const [active, setActive] = useState<HeatmapCell | null>(null);

  const { rows, cols, byKey, maxAbs } = useMemo(() => {
    const rowSet = new Set<string>();
    const colSet = new Set<string>();
    const map = new Map<string, HeatmapCell>();
    let max = 0;
    for (const c of cells) {
      const r = lbl(c.pff_passCoverage);
      const p = lbl(c.pff_positionLinedUp);
      rowSet.add(r);
      colSet.add(p);
      map.set(`${r}\u0000${p}`, c);
      if (c.mean_soe != null) max = Math.max(max, Math.abs(c.mean_soe));
    }
    return {
      rows: [...rowSet].sort(),
      cols: [...colSet].sort(),
      byKey: map,
      maxAbs: max,
    };
  }, [cells]);

  return (
    <section aria-label="Mapa de calor SOE" className="rounded-lg border border-slate-700 bg-slate-900 p-4">
      <h2 className="mb-1 text-lg font-semibold text-slate-100">SOE por cobertura y posición</h2>
      <p className="mb-3 text-sm text-slate-300">
        Azul: más separación de la esperada. Rojo: menos separación de la esperada.
      </p>

      <div
        role="tooltip"
        aria-live="polite"
        className="mb-3 min-h-[3.5rem] rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"
      >
        {active ? (
          <dl className="grid grid-cols-2 gap-x-4 gap-y-0.5 sm:grid-cols-5">
            <div>
              <dt className="text-xs text-slate-300">Cobertura</dt>
              <dd>{lbl(active.pff_passCoverage)}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-300">Posición</dt>
              <dd>{lbl(active.pff_positionLinedUp)}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-300">SOE medio</dt>
              <dd>{fmtYards(active.mean_soe)} yd</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-300">Separación media</dt>
              <dd>{fmtYards(active.mean_separation)} yd</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-300">Rutas (n)</dt>
              <dd>{active.n}</dd>
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
              <th className="px-2 py-1 text-left text-xs font-medium text-slate-300">Cobertura \ Posición</th>
              {cols.map((c) => (
                <th key={c} scope="col" className="px-2 py-1 text-center text-xs font-medium text-slate-300">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r}>
                <th scope="row" className="whitespace-nowrap px-2 py-1 text-left text-xs font-medium text-slate-200">
                  {r}
                </th>
                {cols.map((c) => {
                  const cell = byKey.get(`${r}\u0000${c}`);
                  if (!cell) {
                    return (
                      <td
                        key={c}
                        aria-hidden="true"
                        className="h-10 min-w-[3.5rem] rounded bg-slate-800/40"
                      />
                    );
                  }
                  return (
                    <td key={c} className="p-0">
                      <button
                        type="button"
                        onMouseEnter={() => setActive(cell)}
                        onMouseLeave={() => setActive(null)}
                        onFocus={() => setActive(cell)}
                        onBlur={() => setActive(null)}
                        aria-label={`${r}, ${c}: SOE ${fmtYards(cell.mean_soe)} yardas, separación ${fmtYards(
                          cell.mean_separation,
                        )} yardas, ${cell.n} rutas`}
                        style={{ backgroundColor: cellColor(cell.mean_soe, maxAbs) }}
                        className="h-10 w-full min-w-[3.5rem] rounded px-1 text-xs font-semibold text-white focus:outline-none focus:ring-2 focus:ring-white"
                      >
                        {fmtYards(cell.mean_soe)}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex items-center gap-3 text-xs text-slate-200" aria-label="Leyenda de color">
        <span>{maxAbs > 0 ? `−${maxAbs.toFixed(2)} yd` : '−'}</span>
        <div
          className="h-3 w-48 rounded"
          style={{
            background: `linear-gradient(to right, rgba(${NEGATIVE_RGB}, 1), ${NEUTRAL_BG}, rgba(${POSITIVE_RGB}, 1))`,
          }}
        />
        <span>{maxAbs > 0 ? `+${maxAbs.toFixed(2)} yd` : '+'}</span>
        <span className="text-slate-300">Centro: 0 yd (separación igual a la esperada)</span>
      </div>
    </section>
  );
}

export default Heatmap;
