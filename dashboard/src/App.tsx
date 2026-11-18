import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { getBpiSummary, getHeatmap, getPlay, getPlayers, getPlays } from './api/client'
import type { ExtraParams } from './api/client'
import type { HeatmapCell, PlayDetailResponse, PlaySoe } from './api/types'
import { useApi } from './hooks/useApi'
import { ALL, initialBpiFilters, initialSoeFilters, toggle } from './lib/filters'
import type { BpiFilters, SoeFilters } from './lib/filters'
import { groupRushers } from './lib/bpi'
import { DASH, fmtBpi, fmtPct, fmtYards } from './lib/format'
import { bpiKpis, soeKpis } from './lib/kpi'
import DxdMatrix from './components/DxdMatrix'
import FieldView from './components/FieldView'
import FilterBar, { initialSoeExtras } from './components/FilterBar'
import type { SoeExtras } from './components/FilterBar'
import Header from './components/Header'
import Heatmap from './components/Heatmap'
import KpiCards from './components/KpiCards'
import type { KpiCardData } from './components/KpiCards'
import MethodologyPanel, { BpiExplanation } from './components/MethodologyPanel'
import { PlayList } from './components/PlayList'
import { ReceiverRanking } from './components/ReceiverRanking'
import RushersChart from './components/RushersChart'
import { SectionState } from './components/StateViews'
import Tabs from './components/Tabs'
import type { TabId } from './components/Tabs'
import TeamRanking from './components/TeamRanking'

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="min-w-0 space-y-3">
      <h2 className="text-lg font-semibold text-slate-50">{title}</h2>
      {children}
    </section>
  )
}

/** "Todos" or empty string means no filter. */
function teamParam(v: string): string | undefined {
  return v === ALL || v === '' ? undefined : v
}

function positiveInt(v: string): number | undefined {
  const n = Number(v)
  return v !== '' && Number.isInteger(n) && n >= 1 ? n : undefined
}

/** Coverage whose routes show the largest weighted mean separation. */
function bestCoverage(cells: HeatmapCell[]): { name: string; sep: number } | null {
  const acc = new Map<string, { w: number; sum: number }>()
  for (const c of cells) {
    if (c.pff_passCoverage == null || c.mean_separation == null || c.n <= 0) continue
    const g = acc.get(c.pff_passCoverage) ?? { w: 0, sum: 0 }
    g.w += c.n
    g.sum += c.n * c.mean_separation
    acc.set(c.pff_passCoverage, g)
  }
  let best: { name: string; sep: number } | null = null
  for (const [name, g] of acc) {
    const sep = g.sum / g.w
    if (best === null || sep > best.sep) best = { name, sep }
  }
  return best
}

interface SoeTabProps {
  filters: SoeFilters
  extras: SoeExtras
  searchTerm: string
  offset: number
  selectedPlay: PlaySoe | null
  onSelectReceiver: (id: number) => void
  onSelectPlay: (p: PlaySoe) => void
  onPageChange: (offset: number) => void
}

function SoeTab({
  filters,
  extras,
  searchTerm,
  offset,
  selectedPlay,
  onSelectReceiver,
  onSelectPlay,
  onPageChange,
}: SoeTabProps) {
  const week = extras.week === ALL ? undefined : Number(extras.week)
  const defExtra: ExtraParams = { team: teamParam(extras.defTeam), week }
  const playersExtra: ExtraParams = {
    team: teamParam(extras.recvTeam),
    week,
    search: searchTerm.trim() || undefined,
    minN: positiveInt(extras.minN),
  }
  // The selected receiver is not part of the heatmap/players query, so it is left out of those deps.
  const { coverage, coverageType, position, onlyTargets } = filters

  const heatmap = useApi(
    () => getHeatmap(filters, defExtra),
    [coverage, coverageType, position, onlyTargets, extras.defTeam, extras.week],
    (d) => d.cells.length === 0,
  )
  const players = useApi(
    () => getPlayers(filters, playersExtra),
    [coverage, coverageType, position, onlyTargets, extras.recvTeam, extras.week, searchTerm, extras.minN],
    (d) => d.players.length === 0,
  )
  const plays = useApi(
    () => getPlays(filters, filters.selectedReceiver, offset, defExtra),
    [coverage, coverageType, position, onlyTargets, extras.defTeam, extras.week, filters.selectedReceiver, offset],
    (d) => d.plays.length === 0,
  )
  const detail = useApi<PlayDetailResponse | null>(
    () => (selectedPlay ? getPlay(selectedPlay.gameId, selectedPlay.playId) : Promise.resolve(null)),
    [selectedPlay?.gameId, selectedPlay?.playId],
  )

  const cards: KpiCardData[] = useMemo(() => {
    const cells = heatmap.data?.cells ?? []
    const list = players.data?.players ?? []
    const k = soeKpis(cells, list)
    const hasCells = cells.length > 0
    let best: (typeof list)[number] | null = null
    for (const p of list) {
      if (p.mean_soe != null && (best === null || p.mean_soe > (best.mean_soe ?? -Infinity))) best = p
    }
    const cov = bestCoverage(cells)
    return [
      { label: 'Total de rutas', value: hasCells ? k.routes.toLocaleString('es-MX') : null, status: heatmap.status },
      { label: 'Separación real promedio', value: hasCells ? fmtYards(k.meanSep) : null, hint: 'yardas', status: heatmap.status },
      {
        label: 'Mejor receptor por SOE',
        value: best ? (best.displayName ?? String(best.nflId)) : null,
        hint: best ? `SOE ${fmtBpi(best.mean_soe)} · ${best.n} rutas` : undefined,
        status: players.status,
      },
      {
        label: 'Cobertura que más separación permite',
        value: cov ? cov.name : null,
        hint: cov ? `${fmtYards(cov.sep)} yardas` : undefined,
        status: heatmap.status,
      },
    ]
  }, [heatmap.data, heatmap.status, players.data, players.status])

  return (
    <div className="space-y-6">
      <KpiCards cards={cards} />
      <Section title="Mapa de calor: SOE por cobertura y posición">
        <SectionState status={heatmap.status} onRetry={heatmap.retry}>
          <Heatmap cells={heatmap.data?.cells ?? []} />
        </SectionState>
      </Section>
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Section title="Ranking de receptores">
          <SectionState status={players.status} onRetry={players.retry}>
            <ReceiverRanking
              players={players.data?.players ?? []}
              selectedId={filters.selectedReceiver}
              onSelect={onSelectReceiver}
            />
          </SectionState>
        </Section>
        <Section title="Jugadas">
          <SectionState status={plays.status} onRetry={plays.retry}>
            <PlayList
              plays={plays.data?.plays ?? []}
              total={plays.data?.total ?? 0}
              offset={offset}
              selected={selectedPlay}
              onSelect={onSelectPlay}
              onPageChange={onPageChange}
            />
          </SectionState>
        </Section>
      </div>
      <FieldView
        selectedPlay={selectedPlay}
        status={detail.status}
        detail={detail.data ?? undefined}
        error={detail.error}
        onRetry={detail.retry}
      />
    </div>
  )
}

interface BpiTabProps {
  filters: BpiFilters
  team: string
}

function BpiTab({ filters, team }: BpiTabProps) {
  const extra: ExtraParams = { team: teamParam(team) }
  const { down, distanceBucket, numRushers, coverage } = filters

  const summary = useApi(
    () => getBpiSummary(filters, extra),
    [down, distanceBucket, numRushers, coverage, team],
    (d) => d.total_plays === 0,
  )
  // The down-by-distance matrix always shows every down and distance: those two filters are dropped.
  const dxd = useApi(
    () => getBpiSummary({ ...filters, down: ALL, distanceBucket: ALL }, extra),
    [numRushers, coverage, team],
    (d) => d.down_distance.length === 0,
  )

  const cards: KpiCardData[] = useMemo(() => {
    if (!summary.data) {
      return ['Jugadas de pase', 'Tasa de presión', 'Yardas permitidas promedio', 'Jugadas con presión'].map(
        (label) => ({ label, value: summary.status === 'loading' ? null : DASH, status: summary.status }),
      )
    }
    const k = bpiKpis(summary.data)
    return [
      { label: 'Jugadas de pase', value: k.totalPlays.toLocaleString('es-MX'), status: summary.status },
      { label: 'Tasa de presión', value: fmtPct(k.pressureRate), status: summary.status },
      { label: 'Yardas permitidas promedio', value: fmtYards(k.meanYardsAllowed), status: summary.status },
      { label: 'Jugadas con presión', value: k.totalPressures.toLocaleString('es-MX'), status: summary.status },
    ]
  }, [summary.data, summary.status])

  const groups = useMemo(() => groupRushers(summary.data?.by_rushers ?? []), [summary.data])

  return (
    <div className="space-y-6">
      <BpiExplanation />
      <KpiCards cards={cards} />
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Section title="Tasa de presión por número de rushers">
          <SectionState status={summary.status} onRetry={summary.retry}>
            <RushersChart groups={groups} />
          </SectionState>
        </Section>
        <Section title="BPI por down y distancia">
          <SectionState status={dxd.status} onRetry={dxd.retry}>
            <DxdMatrix cells={dxd.data?.down_distance ?? []} />
          </SectionState>
        </Section>
      </div>
      <Section title="Ranking de equipos defensivos">
        <SectionState status={summary.status} onRetry={summary.retry}>
          <TeamRanking rows={summary.data?.defense_ranking ?? []} />
        </SectionState>
      </Section>
    </div>
  )
}

export default function App() {
  const [tab, setTab] = useState<TabId>('soe')
  const [soeFilters, setSoeFilters] = useState<SoeFilters>(initialSoeFilters)
  const [soeExtras, setSoeExtras] = useState<SoeExtras>(initialSoeExtras)
  const [bpiFilters, setBpiFilters] = useState<BpiFilters>(initialBpiFilters)
  const [bpiTeam, setBpiTeam] = useState<string>(ALL)
  const [offset, setOffset] = useState(0)
  const [selectedPlay, setSelectedPlay] = useState<PlaySoe | null>(null)
  const [searchTerm, setSearchTerm] = useState('')

  // Debounce the receiver search so each keystroke does not fire a request.
  useEffect(() => {
    const t = window.setTimeout(() => setSearchTerm(soeExtras.search), 300)
    return () => window.clearTimeout(t)
  }, [soeExtras.search])

  const handleSoeChange = (next: SoeFilters) => {
    setSoeFilters(next)
    setOffset(0)
  }
  const handleExtrasChange = (next: SoeExtras) => {
    setSoeExtras(next)
    setOffset(0)
  }
  const handleSelectReceiver = (id: number) => {
    setSoeFilters((prev) => ({ ...prev, selectedReceiver: toggle(prev.selectedReceiver, id) }))
    setOffset(0)
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <Header />
      <MethodologyPanel />
      <Tabs tab={tab} onChange={setTab} />
      <main className="space-y-6 px-4 py-6 sm:px-6">
        <FilterBar
          tab={tab === 'soe' ? 'SOE' : 'BPI'}
          soeFilters={soeFilters}
          onSoeChange={handleSoeChange}
          soeExtras={soeExtras}
          onSoeExtrasChange={handleExtrasChange}
          bpiFilters={bpiFilters}
          onBpiChange={setBpiFilters}
          bpiTeam={bpiTeam}
          onBpiTeamChange={setBpiTeam}
        />
        <div role="tabpanel" id="panel-soe" aria-labelledby="tab-soe" hidden={tab !== 'soe'}>
          {tab === 'soe' && (
            <SoeTab
              filters={soeFilters}
              extras={soeExtras}
              searchTerm={searchTerm}
              offset={offset}
              selectedPlay={selectedPlay}
              onSelectReceiver={handleSelectReceiver}
              onSelectPlay={setSelectedPlay}
              onPageChange={setOffset}
            />
          )}
        </div>
        <div role="tabpanel" id="panel-bpi" aria-labelledby="tab-bpi" hidden={tab !== 'bpi'}>
          {tab === 'bpi' && <BpiTab filters={bpiFilters} team={bpiTeam} />}
        </div>
      </main>
    </div>
  )
}
