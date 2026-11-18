import type { PlayerSoe } from '../api/types'
import { DASH, fmtBpi, fmtYards } from '../lib/format'

export interface ReceiverRankingProps {
  players: PlayerSoe[]
  selectedId: number | undefined
  /** Called with the clicked receiver id. The parent toggles the selection and resets offset to 0. */
  onSelect: (nflId: number) => void
}

export function ReceiverRanking({ players, selectedId, onSelect }: ReceiverRankingProps) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-700 bg-slate-900">
      <table className="w-full text-left text-sm text-slate-100">
        <caption className="px-3 py-2 text-left text-base font-semibold text-slate-50">
          Ranking de receptores
        </caption>
        <thead className="border-b border-slate-700 text-slate-300">
          <tr>
            <th scope="col" className="px-3 py-2">#</th>
            <th scope="col" className="px-3 py-2">Receptor</th>
            <th scope="col" className="px-3 py-2">Equipo</th>
            <th scope="col" className="px-3 py-2 text-right">Rutas</th>
            <th scope="col" className="px-3 py-2 text-right">Separación media (yd)</th>
            <th scope="col" className="px-3 py-2 text-right">SOE medio (yd)</th>
          </tr>
        </thead>
        <tbody role="listbox" aria-label="Receptores" className="contents">
          {players.map((p, i) => {
            const selected = p.nflId === selectedId
            const soeColor =
              p.mean_soe == null || p.mean_soe === 0
                ? 'text-slate-100'
                : p.mean_soe > 0
                  ? 'text-sky-300'
                  : 'text-red-300'
            return (
              <tr
                key={p.nflId}
                role="option"
                aria-selected={selected}
                tabIndex={0}
                onClick={() => onSelect(p.nflId)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    onSelect(p.nflId)
                  }
                }}
                className={`cursor-pointer border-b border-slate-800 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-sky-300 ${
                  selected ? 'bg-slate-700' : ''
                }`}
              >
                <td className="px-3 py-2">{i + 1}</td>
                <td className="px-3 py-2">{p.displayName ?? String(p.nflId)}</td>
                <td className="px-3 py-2">{p.team ?? DASH}</td>
                <td className="px-3 py-2 text-right">{p.n}</td>
                <td className="px-3 py-2 text-right">{fmtYards(p.mean_separation)}</td>
                <td className={`px-3 py-2 text-right font-medium ${soeColor}`}>{fmtBpi(p.mean_soe)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
