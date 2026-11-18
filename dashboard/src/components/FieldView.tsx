import { ApiError } from '../api/client'
import type { PlayDetailResponse, PlaySoe } from '../api/types'
import type { ApiStatus } from '../hooks/useApi'
import { fmtYards } from '../lib/format'
import { pairReceivers } from '../lib/field'
import { EmptyState, ErrorState, LoadingState } from './StateViews'

export const NO_PLAY_TEXT = 'Selecciona una jugada'
export const NOT_FOUND_TEXT = 'Jugada no encontrada'

const RESULT_LABELS: Record<string, string> = {
  C: 'Completo',
  I: 'Incompleto',
  IN: 'Intercepción',
  S: 'Sack',
  R: 'Corrida',
}

const FIELD_W = 120
const FIELD_H = 53.3
const HASH_Y = [23.58, 29.72]

export interface FieldViewProps {
  /** Play chosen in the PlayList; null while no play is selected. */
  selectedPlay: PlaySoe | null
  /** Status of the getPlay request (useApi status). Ignored while selectedPlay is null. */
  status: ApiStatus
  /** Response of api/soe/play/{game_id}/{play_id}. */
  detail: PlayDetailResponse | undefined
  /** Error of the getPlay request; an ApiError with status 404 shows "Jugada no encontrada". */
  error?: unknown
  onRetry: () => void
}

function resultText(play: PlaySoe): string {
  if (play.result == null && play.play_result == null) return '—'
  const label = play.result != null ? RESULT_LABELS[play.result] ?? play.result : ''
  const yards = play.play_result != null ? `${play.play_result} yd` : ''
  return [label, yards].filter(Boolean).join(' · ')
}

function FieldSvg({ detail }: { detail: PlayDetailResponse }) {
  const lines = pairReceivers(detail)
  const coverage = detail.players.filter((p) => p.pff_role === 'Coverage' && p.x != null && p.y != null)
  const yardLines: number[] = []
  for (let x = 10; x <= 110; x += 5) yardLines.push(x)
  const hashes: number[] = []
  for (let x = 11; x < 110; x += 1) hashes.push(x)

  return (
    <svg
      viewBox={`0 0 ${FIELD_W} ${FIELD_H}`}
      className="w-full rounded-md border border-slate-700"
      role="img"
      aria-label="Campo de futbol americano con receptores y defensores en el momento del pase"
    >
      <rect x={0} y={0} width={FIELD_W} height={FIELD_H} fill="#14532d" />
      <rect x={0} y={0} width={10} height={FIELD_H} fill="#0f3d22" />
      <rect x={110} y={0} width={10} height={FIELD_H} fill="#0f3d22" />
      {yardLines.map((x) => (
        <line key={x} x1={x} y1={0} x2={x} y2={FIELD_H} stroke="#e2e8f0" strokeOpacity={0.55} strokeWidth={x === 10 || x === 110 ? 0.35 : 0.2} />
      ))}
      {hashes.map((x) =>
        HASH_Y.map((y) => (
          <line key={`${x}-${y}`} x1={x} y1={y - 0.4} x2={x} y2={y + 0.4} stroke="#e2e8f0" strokeOpacity={0.45} strokeWidth={0.12} />
        )),
      )}
      {yardLines
        .filter((x) => x > 10 && x < 110 && x % 10 === 0)
        .map((x) => (
          <text key={`t${x}`} x={x} y={FIELD_H - 2} fontSize={2} textAnchor="middle" fill="#e2e8f0" fillOpacity={0.7}>
            {x <= 60 ? x - 10 : 110 - x}
          </text>
        ))}

      {coverage.map((c, i) => (
        <rect
          key={`d${c.nflId ?? i}`}
          x={(c.x as number) - 0.5}
          y={(c.y as number) - 0.5}
          width={1}
          height={1}
          fill="#f87171"
          fillOpacity={0.85}
        />
      ))}

      {lines.map(
        (l) =>
          l.dx != null &&
          l.dy != null && (
            <g key={`l${l.nflId}`}>
              <line
                x1={l.rx}
                y1={l.ry}
                x2={l.dx}
                y2={l.dy}
                stroke="#fde047"
                strokeWidth={0.25}
                strokeDasharray="0.6 0.6"
              />
              <text
                x={(l.rx + l.dx) / 2}
                y={(l.ry + l.dy) / 2 - 0.6}
                fontSize={1.6}
                textAnchor="middle"
                fill="#fef08a"
                stroke="#000"
                strokeWidth={0.12}
                paintOrder="stroke"
              >
                {fmtYards(l.separation)}
              </text>
            </g>
          ),
      )}

      {lines.map((l) => (
        <g key={`r${l.nflId}`}>
          {l.isTarget ? (
            <polygon
              points={`${l.rx},${l.ry - 1.4} ${l.rx + 1.4},${l.ry} ${l.rx},${l.ry + 1.4} ${l.rx - 1.4},${l.ry}`}
              fill="#38bdf8"
              stroke="#ffffff"
              strokeWidth={0.3}
            />
          ) : (
            <circle cx={l.rx} cy={l.ry} r={0.9} fill="#38bdf8" stroke="#0f172a" strokeWidth={0.2} />
          )}
          <text
            x={l.rx}
            y={l.ry - 2}
            fontSize={1.8}
            textAnchor="middle"
            fill="#ffffff"
            stroke="#000"
            strokeWidth={0.15}
            paintOrder="stroke"
          >
            {l.name}
          </text>
        </g>
      ))}
    </svg>
  )
}

function Legend() {
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-slate-200" aria-label="Leyenda del campo">
      <li className="flex items-center gap-2">
        <span className="inline-block h-3 w-3 rounded-full bg-sky-400" aria-hidden="true" /> Receptor
      </li>
      <li className="flex items-center gap-2">
        <span className="inline-block h-3 w-3 rotate-45 border border-white bg-sky-400" aria-hidden="true" /> Objetivo probable
      </li>
      <li className="flex items-center gap-2">
        <span className="inline-block h-3 w-3 bg-red-400" aria-hidden="true" /> Defensor
      </li>
      <li className="flex items-center gap-2">
        <span className="inline-block w-6 border-t-2 border-dotted border-yellow-300" aria-hidden="true" /> Defensor más cercano (separación en yardas)
      </li>
    </ul>
  )
}

export default function FieldView({ selectedPlay, status, detail, error, onRetry }: FieldViewProps) {
  const title = <h2 className="text-lg font-semibold text-slate-50">Vista de campo</h2>

  let body
  if (selectedPlay == null) {
    body = <EmptyState message={NO_PLAY_TEXT} />
  } else if (status === 'loading') {
    body = <LoadingState />
  } else if (status === 'error') {
    body =
      error instanceof ApiError && error.status === 404 ? (
        <EmptyState message={NOT_FOUND_TEXT} />
      ) : (
        <ErrorState onRetry={onRetry} />
      )
  } else if (status === 'empty' || detail == null) {
    body = <EmptyState />
  } else {
    const lines = pairReceivers(detail)
    body = (
      <div className="flex flex-col gap-3">
        <div className="text-sm text-slate-200">
          <p>
            <span className="font-semibold text-slate-50">Descripción: </span>
            {selectedPlay.playDescription ?? '—'}
          </p>
          <p>
            <span className="font-semibold text-slate-50">Resultado: </span>
            {resultText(selectedPlay)}
          </p>
        </div>
        <FieldSvg detail={detail} />
        <Legend />
        {lines.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-200">
              <thead className="text-slate-50">
                <tr className="border-b border-slate-700">
                  <th className="py-1 pr-3 font-semibold">Receptor</th>
                  <th className="py-1 pr-3 text-right font-semibold">Separación (yd)</th>
                  <th className="py-1 pr-3 text-right font-semibold">Separación esperada (yd)</th>
                  <th className="py-1 text-right font-semibold">SOE (yd)</th>
                </tr>
              </thead>
              <tbody>
                {lines.map((l) => (
                  <tr key={l.nflId} className="border-b border-slate-800">
                    <td className="py-1 pr-3">
                      {l.name}
                      {l.isTarget ? ' ★' : ''}
                    </td>
                    <td className="py-1 pr-3 text-right tabular-nums">{fmtYards(l.separation)}</td>
                    <td className="py-1 pr-3 text-right tabular-nums">{fmtYards(l.expected)}</td>
                    <td className="py-1 text-right tabular-nums">{fmtYards(l.soe)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    )
  }

  return (
    <section
      className="flex flex-col gap-3 rounded-lg border border-slate-700 bg-slate-900 p-4"
      aria-busy={selectedPlay != null && status === 'loading'}
    >
      {title}
      {body}
    </section>
  )
}
