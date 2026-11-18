import type { ReactNode } from 'react'

export const EMPTY_TEXT = 'Sin datos para los filtros seleccionados'
export const ERROR_TEXT = 'No se pudieron cargar los datos'

export function LoadingState({ label = 'Cargando…', className = '' }: { label?: string; className?: string }) {
  return (
    <div
      role="status"
      aria-busy="true"
      className={`flex items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-900 p-6 text-slate-200 ${className}`}
    >
      <span className="h-4 w-4 animate-pulse rounded-full bg-slate-400" aria-hidden="true" />
      <span>{label}</span>
    </div>
  )
}

export function EmptyState({ message = EMPTY_TEXT, className = '' }: { message?: string; className?: string }) {
  return (
    <div
      role="note"
      className={`flex items-center justify-center rounded-lg border border-dashed border-slate-600 bg-slate-900 p-6 text-center text-slate-200 ${className}`}
    >
      {message}
    </div>
  )
}

export function ErrorState({ onRetry, className = '' }: { onRetry: () => void; className?: string }) {
  return (
    <div
      role="alert"
      className={`flex flex-col items-center justify-center gap-3 rounded-lg border border-red-400 bg-slate-900 p-6 text-center text-slate-100 ${className}`}
    >
      <span>{ERROR_TEXT}</span>
      <button
        type="button"
        onClick={onRetry}
        className="rounded-md border border-slate-300 bg-slate-800 px-3 py-1 text-slate-50 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-300"
      >
        Reintentar
      </button>
    </div>
  )
}

export interface SectionStateProps {
  status: 'loading' | 'empty' | 'error' | 'ready'
  onRetry: () => void
  /** Rendered only when status is 'ready'. */
  children: ReactNode
  emptyMessage?: string
  className?: string
}

/** Chooses Loading, Empty, Error or the content according to the useApi status. */
export function SectionState({ status, onRetry, children, emptyMessage, className }: SectionStateProps) {
  if (status === 'loading') return <LoadingState className={className} />
  if (status === 'error') return <ErrorState onRetry={onRetry} className={className} />
  if (status === 'empty') return <EmptyState message={emptyMessage} className={className} />
  return <>{children}</>
}
