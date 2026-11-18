import { getFilters } from '../api/client'
import { useApi } from '../hooks/useApi'
import { ALL, resetBpiFilters, resetSoeFilters } from '../lib/filters'
import type { BpiFilters, SoeFilters } from '../lib/filters'
import { ErrorState, LoadingState } from './StateViews'

/** Extra SOE filters not held in SoeFilters. Strings; "Todos"/"" mean no filter. */
export interface SoeExtras {
  /** Defensive team (heatmap and plays). */
  defTeam: string
  /** Receiver team (players ranking). */
  recvTeam: string
  week: string
  /** Receiver name search. */
  search: string
  /** Minimum routes per receiver (digits only, "" = backend default). */
  minN: string
}

export const initialSoeExtras: SoeExtras = { defTeam: ALL, recvTeam: ALL, week: ALL, search: '', minN: '' }

export interface FilterBarProps {
  /** Selected tab. Controls which filter set is shown. */
  tab: 'SOE' | 'BPI'
  soeFilters: SoeFilters
  onSoeChange: (next: SoeFilters) => void
  soeExtras: SoeExtras
  onSoeExtrasChange: (next: SoeExtras) => void
  bpiFilters: BpiFilters
  onBpiChange: (next: BpiFilters) => void
  /** Defensive team for the BPI tab: "Todos" or a team abbreviation. Sent by App as ExtraParams.team. */
  bpiTeam: string
  onBpiTeamChange: (team: string) => void
}

/** Static options: `api/filters` has no list for the number of rushers. */
const RUSHER_OPTIONS = ['2', '3', '4', '5', '6', '7', '8']

interface SelectProps {
  id: string
  label: string
  value: string
  options: string[]
  onChange: (v: string) => void
}

function Select({ id, label, value, options, onChange }: SelectProps) {
  return (
    <div className="flex min-w-[10rem] flex-col gap-1">
      <label htmlFor={id} className="text-sm text-slate-300">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-slate-500 bg-slate-800 px-2 py-1 text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-300"
      >
        <option value={ALL}>{ALL}</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  )
}

/** Filter controls populated from `api/filters` (requested once; the component stays mounted across tabs). */
export function FilterBar({
  tab,
  soeFilters,
  onSoeChange,
  soeExtras,
  onSoeExtrasChange,
  bpiFilters,
  onBpiChange,
  bpiTeam,
  onBpiTeamChange,
}: FilterBarProps) {
  const { status, data, retry } = useApi(() => getFilters(), [])

  if (status === 'loading' && !data) return <LoadingState label="Cargando filtros…" />
  if (status === 'error' || !data) return <ErrorState onRetry={retry} />

  const coverages = data.pff_passCoverage ?? []
  const coverageTypes = data.pff_passCoverageType ?? []
  const positions = data.pff_positionLinedUp ?? []
  const buckets = data.distance_bucket ?? []
  const downs = (data.down ?? []).map(String)
  const teams = data.team ?? []
  const weeks = (data.week ?? []).map(String)

  const reset = () => {
    if (tab === 'SOE') {
      onSoeChange(resetSoeFilters())
      onSoeExtrasChange({ ...initialSoeExtras })
    } else {
      onBpiChange(resetBpiFilters())
      onBpiTeamChange(ALL)
    }
  }

  return (
    <section
      aria-label="Filtros"
      aria-busy={status === 'loading' ? 'true' : undefined}
      className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-700 bg-slate-900 p-4"
    >
      {tab === 'SOE' ? (
        <>
          <Select
            id="f-coverage"
            label="Cobertura"
            value={soeFilters.coverage}
            options={coverages}
            onChange={(v) => onSoeChange({ ...soeFilters, coverage: v })}
          />
          <Select
            id="f-coverage-type"
            label="Tipo de cobertura"
            value={soeFilters.coverageType}
            options={coverageTypes}
            onChange={(v) => onSoeChange({ ...soeFilters, coverageType: v })}
          />
          <Select
            id="f-def-team"
            label="Equipo defensivo"
            value={soeExtras.defTeam}
            options={teams}
            onChange={(v) => onSoeExtrasChange({ ...soeExtras, defTeam: v })}
          />
          <Select
            id="f-recv-team"
            label="Equipo del receptor"
            value={soeExtras.recvTeam}
            options={teams}
            onChange={(v) => onSoeExtrasChange({ ...soeExtras, recvTeam: v })}
          />
          <Select
            id="f-week"
            label="Semana"
            value={soeExtras.week}
            options={weeks}
            onChange={(v) => onSoeExtrasChange({ ...soeExtras, week: v })}
          />
          <div className="flex min-w-[10rem] flex-col gap-1">
            <label htmlFor="f-search" className="text-sm text-slate-300">
              Buscar receptor
            </label>
            <input
              id="f-search"
              type="search"
              value={soeExtras.search}
              placeholder="Nombre"
              onChange={(e) => onSoeExtrasChange({ ...soeExtras, search: e.target.value })}
              className="rounded-md border border-slate-500 bg-slate-800 px-2 py-1 text-slate-50 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-300"
            />
          </div>
          <div className="flex w-32 flex-col gap-1">
            <label htmlFor="f-min-n" className="text-sm text-slate-300">
              Mínimo de rutas
            </label>
            <input
              id="f-min-n"
              type="number"
              min={1}
              inputMode="numeric"
              value={soeExtras.minN}
              onChange={(e) => onSoeExtrasChange({ ...soeExtras, minN: e.target.value.replace(/\D/g, '') })}
              className="rounded-md border border-slate-500 bg-slate-800 px-2 py-1 text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-300"
            />
          </div>
          <Select
            id="f-position"
            label="Posición del receptor"
            value={soeFilters.position}
            options={positions}
            onChange={(v) => onSoeChange({ ...soeFilters, position: v })}
          />
          <label className="flex items-center gap-2 pb-1 text-slate-50">
            <input
              type="checkbox"
              checked={soeFilters.onlyTargets}
              onChange={(e) => onSoeChange({ ...soeFilters, onlyTargets: e.target.checked })}
              className="h-4 w-4 accent-sky-400"
            />
            Solo objetivos probables
          </label>
        </>
      ) : (
        <>
          <Select
            id="f-bpi-team"
            label="Equipo defensivo"
            value={bpiTeam}
            options={teams}
            onChange={onBpiTeamChange}
          />
          <Select
            id="f-bpi-coverage"
            label="Cobertura"
            value={bpiFilters.coverage}
            options={coverages}
            onChange={(v) => onBpiChange({ ...bpiFilters, coverage: v })}
          />
          <Select
            id="f-down"
            label="Down"
            value={bpiFilters.down}
            options={downs}
            onChange={(v) => onBpiChange({ ...bpiFilters, down: v })}
          />
          <Select
            id="f-distance"
            label="Distancia"
            value={bpiFilters.distanceBucket}
            options={buckets}
            onChange={(v) => onBpiChange({ ...bpiFilters, distanceBucket: v })}
          />
          <Select
            id="f-rushers"
            label="Número de rushers"
            value={bpiFilters.numRushers}
            options={RUSHER_OPTIONS}
            onChange={(v) => onBpiChange({ ...bpiFilters, numRushers: v })}
          />
        </>
      )}
      <button
        type="button"
        onClick={reset}
        className="rounded-md border border-slate-300 bg-slate-800 px-3 py-1 text-slate-50 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-300"
      >
        Limpiar filtros
      </button>
    </section>
  )
}

export default FilterBar
