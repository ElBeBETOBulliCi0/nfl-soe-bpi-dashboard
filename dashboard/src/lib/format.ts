export const DASH = '—';

/** Yards with two decimals; "—" for null/undefined/NaN. */
export function fmtYards(v: number | null | undefined): string {
  return v == null || Number.isNaN(v) ? DASH : v.toFixed(2);
}

/** Fraction (0 to 1) as a percentage with one decimal; "—" for null/undefined/NaN. */
export function fmtPct(v: number | null | undefined): string {
  return v == null || Number.isNaN(v) ? DASH : `${(v * 100).toFixed(1)}%`;
}

/** BPI with two decimals and a "+" prefix when positive; "—" for null/undefined/NaN. */
export function fmtBpi(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return DASH;
  return `${v > 0 ? '+' : ''}${v.toFixed(2)}`;
}
