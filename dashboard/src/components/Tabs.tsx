export type TabId = 'soe' | 'bpi'

export interface TabsProps {
  tab: TabId
  onChange: (tab: TabId) => void
}

const TABS: { id: TabId; label: string }[] = [
  { id: 'soe', label: 'SOE' },
  { id: 'bpi', label: 'BPI' },
]

export default function Tabs({ tab, onChange }: TabsProps) {
  return (
    <div role="tablist" aria-label="Métricas" className="flex gap-2 border-b border-slate-700 px-4 pt-3 sm:px-6">
      {TABS.map((t) => {
        const selected = t.id === tab
        return (
          <button
            key={t.id}
            type="button"
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={selected}
            aria-controls={`panel-${t.id}`}
            onClick={() => onChange(t.id)}
            className={`rounded-t-md border-b-2 px-4 py-2 font-semibold focus:outline-none focus:ring-2 focus:ring-sky-300 ${
              selected
                ? 'border-sky-300 bg-slate-800 text-slate-50'
                : 'border-transparent text-slate-300 hover:bg-slate-800 hover:text-slate-50'
            }`}
          >
            {t.label}
          </button>
        )
      })}
    </div>
  )
}
