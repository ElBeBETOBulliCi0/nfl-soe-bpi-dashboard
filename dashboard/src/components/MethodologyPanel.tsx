import { useState } from 'react'

export const BPI_EXPLANATION = 'Positivo: la presión compensa las yardas cedidas; negativo: el blitz salió caro.'

/** Static one-line BPI explanation, shown on the BPI tab outside the Methodology_Panel. */
export function BpiExplanation() {
  return <p className="px-4 py-2 text-sm text-slate-200 sm:px-6">{BPI_EXPLANATION}</p>
}

export default function MethodologyPanel() {
  const [open, setOpen] = useState(false)
  return (
    <section className="border-b border-slate-700 bg-slate-900 px-4 py-3 sm:px-6">
      <button
        type="button"
        aria-expanded={open}
        aria-controls="methodology-body"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 font-semibold text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-300"
      >
        <span aria-hidden="true">{open ? '▾' : '▸'}</span>
        <span>¿Cómo se calcula?</span>
      </button>
      {open && (
        <div id="methodology-body" className="mt-3 space-y-3 text-sm text-slate-200">
          <div>
            <h3 className="font-semibold text-slate-50">SOE (Separación sobre lo esperado)</h3>
            <p>
              Es la distancia entre un receptor y el defensor más cercano en el Release_Frame, menos la separación
              esperada para la misma cobertura y alineación. Un valor positivo indica más separación de la esperada.
            </p>
          </div>
          <div>
            <h3 className="font-semibold text-slate-50">Release_Frame</h3>
            <p>Es el cuadro de seguimiento en el que se lanza el pase.</p>
          </div>
          <div>
            <h3 className="font-semibold text-slate-50">Separación esperada</h3>
            <p>
              Es la separación promedio de las rutas agrupadas por cobertura y posición de alineación del receptor.
            </p>
          </div>
          <div>
            <h3 className="font-semibold text-slate-50">BPI (Índice de bloqueo y presión)</h3>
            <p className="font-mono text-slate-50">
              BPI = (tasa de presión × 100) − (yardas permitidas promedio × 5)
            </p>
            <p>{BPI_EXPLANATION}</p>
          </div>
          <div>
            <h3 className="font-semibold text-slate-50">Rangos de distancia</h3>
            <ul className="list-disc pl-5">
              <li>Short: 1 a 3 yardas</li>
              <li>Medium: 4 a 7 yardas</li>
              <li>Long: 8 yardas o más</li>
            </ul>
          </div>
        </div>
      )}
    </section>
  )
}
