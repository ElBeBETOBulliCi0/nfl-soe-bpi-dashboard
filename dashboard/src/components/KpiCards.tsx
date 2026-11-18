import { DASH } from '../lib/format'
import { LoadingState } from './StateViews'

export interface KpiCardData {
  /** Spanish label shown above the value. */
  label: string
  /** Already formatted value (fmtYards, fmtPct, ...). Null or undefined renders "—". */
  value: string | null | undefined
  /** Source request state. Default 'ready'. 'loading' shows the Loading_State inside the card. */
  status?: 'loading' | 'empty' | 'error' | 'ready'
  /** Optional small text under the value (e.g. units). */
  hint?: string
}

export interface KpiCardsProps {
  /** Four cards per tab. */
  cards: KpiCardData[]
}

/** Four KPI cards: one row of four from 1024 px, one or two columns below. */
export function KpiCards({ cards }: KpiCardsProps) {
  return (
    <section aria-label="Indicadores clave" className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((c) => (
        <div
          key={c.label}
          className="min-w-0 rounded-lg border border-slate-700 bg-slate-900 p-4"
          aria-busy={c.status === 'loading' ? 'true' : undefined}
        >
          <p className="text-sm text-slate-300">{c.label}</p>
          {c.status === 'loading' ? (
            <LoadingState label="Cargando…" className="mt-2 border-0 p-2" />
          ) : (
            <>
              <p className="mt-1 break-words text-3xl font-semibold text-slate-50">{c.value ?? DASH}</p>
              {c.hint ? <p className="mt-1 text-xs text-slate-300">{c.hint}</p> : null}
            </>
          )}
        </div>
      ))}
    </section>
  )
}

export default KpiCards
