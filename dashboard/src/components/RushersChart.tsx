import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { RusherGroupRow } from '../lib/bpi';
import { fmtBpi, fmtPct, fmtYards } from '../lib/format';
import { EmptyState } from './StateViews';

export interface RushersChartProps {
  /** Output of `groupRushers` (keys 3, 4, 5, 6+). */
  groups: RusherGroupRow[];
}

interface ChartDatum extends RusherGroupRow {
  label: string;
  rate: number;
}

interface TooltipProps {
  active?: boolean;
  payload?: { payload: ChartDatum }[];
}

function ChartTooltip({ active, payload }: TooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded border border-slate-500 bg-slate-950 px-3 py-2 text-sm text-slate-100 shadow">
      <div className="mb-1 font-semibold">{d.label}</div>
      <dl className="grid grid-cols-[auto_auto] gap-x-3 gap-y-0.5">
        <dt className="text-slate-300">Tasa de presión</dt>
        <dd className="text-right">{fmtPct(d.pressure_rate)}</dd>
        <dt className="text-slate-300">BPI</dt>
        <dd className="text-right">{fmtBpi(d.bpi)}</dd>
        <dt className="text-slate-300">Yardas permitidas</dt>
        <dd className="text-right">{fmtYards(d.mean_yards_allowed)}</dd>
        <dt className="text-slate-300">Jugadas</dt>
        <dd className="text-right">{d.n_plays}</dd>
        <dt className="text-slate-300">Jugadas con presión</dt>
        <dd className="text-right">{d.n_pressure}</dd>
      </dl>
    </div>
  );
}

export function RushersChart({ groups }: RushersChartProps) {
  const data: ChartDatum[] = groups
    .filter((g) => g.n_plays > 0)
    .map((g) => ({
      ...g,
      label: `${g.key} rushers`,
      rate: g.pressure_rate ?? 0,
    }));

  return (
    <section aria-label="Presión por número de rushers" className="rounded-lg border border-slate-700 bg-slate-900 p-4">
      <h2 className="mb-1 text-lg font-semibold text-slate-100">Tasa de presión por número de rushers</h2>
      <p className="mb-3 text-sm text-slate-300">Porcentaje de jugadas con presión según cuántos rushers envió la defensa.</p>
      {data.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
              <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
              <XAxis dataKey="label" stroke="#cbd5e1" tick={{ fill: '#e2e8f0', fontSize: 12 }} />
              <YAxis
                stroke="#cbd5e1"
                tick={{ fill: '#e2e8f0', fontSize: 12 }}
                tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                domain={[0, (max: number) => Math.min(1, Math.max(0.1, max * 1.15))]}
              />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(148, 163, 184, 0.15)' }} />
              <Bar dataKey="rate" name="Tasa de presión" fill="#38bdf8" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}

export default RushersChart;
