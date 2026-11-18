import type { PlaySoe } from '../api/types'
import { DASH, fmtYards } from '../lib/format'
import { PAGE_SIZE, hasNext, hasPrev, nextOffset, prevOffset } from '../lib/paging'

export interface SelectedPlay {
  gameId: number
  playId: number
}

export interface PlayListProps {
  plays: PlaySoe[]
  total: number
  offset: number
  selected: SelectedPlay | null
  onSelect: (play: PlaySoe) => void
  /** Called with the new offset (steps of 25). */
  onPageChange: (offset: number) => void
}

const RESULT_LABELS: Record<string, string> = {
  C: 'Completo',
  I: 'Incompleto',
  IN: 'Intercepción',
  S: 'Sack',
  R: 'Corrida',
}

export function resultLabel(code: string | null, yards: number | null): string {
  if (code == null || code === '') return yards == null ? DASH : `${yards} yd`
  const label = RESULT_LABELS[code] ?? code
  return yards == null ? label : `${label} (${yards} yd)`
}

export function PlayList({ plays, total, offset, selected, onSelect, onPageChange }: PlayListProps) {
  const showPaging = total > plays.length
  const first = plays.length === 0 ? 0 : offset + 1
  const last = offset + plays.length
  const btn =
    'rounded-md border border-slate-300 bg-slate-800 px-3 py-1 text-slate-50 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-300 disabled:cursor-not-allowed disabled:opacity-40'

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900">
      <h3 className="px-3 py-2 text-base font-semibold text-slate-50">Jugadas</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-100">
          <thead className="border-b border-slate-700 text-slate-300">
            <tr>
              <th scope="col" className="px-3 py-2">Juego</th>
              <th scope="col" className="px-3 py-2">Jugada</th>
              <th scope="col" className="px-3 py-2">Descripción</th>
              <th scope="col" className="px-3 py-2">Resultado</th>
              <th scope="col" className="px-3 py-2 text-right">Rutas</th>
              <th scope="col" className="px-3 py-2 text-right">SOE objetivo (yd)</th>
            </tr>
          </thead>
          <tbody role="listbox" aria-label="Jugadas" className="contents">
            {plays.map((p) => {
              const isSel = selected != null && selected.gameId === p.gameId && selected.playId === p.playId
              return (
                <tr
                  key={`${p.gameId}-${p.playId}`}
                  role="option"
                  aria-selected={isSel}
                  tabIndex={0}
                  onClick={() => onSelect(p)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      onSelect(p)
                    }
                  }}
                  className={`cursor-pointer border-b border-slate-800 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-sky-300 ${
                    isSel ? 'bg-slate-700' : ''
                  }`}
                >
                  <td className="px-3 py-2">{p.gameId}</td>
                  <td className="px-3 py-2">{p.playId}</td>
                  <td className="max-w-md px-3 py-2">{p.playDescription ?? DASH}</td>
                  <td className="whitespace-nowrap px-3 py-2">{resultLabel(p.result, p.play_result)}</td>
                  <td className="px-3 py-2 text-right">{p.n_routes}</td>
                  <td className="px-3 py-2 text-right">{fmtYards(p.target_soe)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {showPaging && (
        <nav aria-label="Paginación de jugadas" className="flex items-center justify-between gap-2 px-3 py-2 text-sm text-slate-200">
          <button type="button" className={btn} disabled={!hasPrev(offset)} onClick={() => onPageChange(prevOffset(offset))}>
            Anterior
          </button>
          <span>
            {first}–{last} de {total}
          </span>
          <button
            type="button"
            className={btn}
            disabled={!hasNext(offset, total) || PAGE_SIZE <= 0}
            onClick={() => onPageChange(nextOffset(offset))}
          >
            Siguiente
          </button>
        </nav>
      )}
    </div>
  )
}
