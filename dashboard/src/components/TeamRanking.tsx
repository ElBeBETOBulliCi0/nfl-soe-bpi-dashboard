import type { BpiDefenseRow } from '../api/types'
import { fmtBpi, fmtPct, fmtYards } from '../lib/format'
import { EmptyState } from './StateViews'

export const NO_TEAM_TEXT = 'Sin equipo'

export interface TeamRankingProps {
  /** Rows in the order returned by the API (Pressure_Rate descending). */
  rows: BpiDefenseRow[]
}

function bpiClass(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v) || v === 0) return 'text-slate-100'
  return v > 0 ? 'text-sky-300' : 'text-red-300'
}

export function TeamRanking({ rows }: TeamRankingProps) {
  if (rows.length === 0) return <EmptyState />

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-700 bg-slate-900">
      <table className="w-full text-left text-sm text-slate-100">
        <caption className="px-3 py-2 text-left text-base font-semibold text-slate-50">
          Ranking de equipos defensivos
        </caption>
        <thead className="border-b border-slate-700 text-slate-300">
          <tr>
            <th scope="col" className="px-3 py-2">#</th>
            <th scope="col" className="px-3 py-2">Equipo</th>
            <th scope="col" className="px-3 py-2 text-right">Jugadas</th>
            <th scope="col" className="px-3 py-2 text-right">Tasa de presión</th>
            <th scope="col" className="px-3 py-2 text-right">Yardas permitidas</th>
            <th scope="col" className="px-3 py-2 text-right">BPI</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={`${r.defensiveTeam ?? 'null'}-${i}`} className="border-b border-slate-800">
              <td className="px-3 py-2">{i + 1}</td>
              <td className="px-3 py-2">{r.defensiveTeam ?? NO_TEAM_TEXT}</td>
              <td className="px-3 py-2 text-right">{r.n_plays}</td>
              <td className="px-3 py-2 text-right">{fmtPct(r.pressure_rate)}</td>
              <td className="px-3 py-2 text-right">{fmtYards(r.mean_yards_allowed)}</td>
              <td className={`px-3 py-2 text-right font-medium ${bpiClass(r.bpi)}`}>{fmtBpi(r.bpi)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default TeamRanking
