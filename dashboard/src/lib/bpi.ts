import type { BpiDownDistanceCell } from '../api/types';

export interface RusherInput {
  num_rushers: number;
  n_plays: number;
  n_pressure: number;
  mean_yards_allowed: number | null;
}

export type RusherKey = '3' | '4' | '5' | '6+';

export interface RusherGroupRow {
  key: RusherKey;
  n_plays: number;
  n_pressure: number;
  pressure_rate: number | null;
  mean_yards_allowed: number | null;
  bpi: number | null;
}

const RUSHER_KEYS: RusherKey[] = ['3', '4', '5', '6+'];

/** bpi = round(rate * 100 - meanYards * 5, 2); null when either input is null. */
export function computeBpi(rate: number | null, meanYards: number | null): number | null {
  if (rate == null || meanYards == null) return null;
  return Math.round((rate * 100 - meanYards * 5) * 100) / 100;
}

/** Groups num_rushers into 3, 4, 5, 6+ (num_rushers < 3 excluded). Never averages `bpi` values. */
export function groupRushers(rows: RusherInput[]): RusherGroupRow[] {
  const acc = new Map<
    RusherKey,
    { n: number; p: number; yardsW: number; yardsSum: number }
  >();
  for (const r of rows) {
    if (r.num_rushers < 3) continue;
    const key: RusherKey = r.num_rushers >= 6 ? '6+' : (String(r.num_rushers) as RusherKey);
    const g = acc.get(key) ?? { n: 0, p: 0, yardsW: 0, yardsSum: 0 };
    g.n += r.n_plays;
    g.p += r.n_pressure;
    if (r.mean_yards_allowed != null) {
      g.yardsW += r.n_plays;
      g.yardsSum += r.n_plays * r.mean_yards_allowed;
    }
    acc.set(key, g);
  }
  return RUSHER_KEYS.filter((k) => acc.has(k)).map((key) => {
    const g = acc.get(key)!;
    const rate = g.n > 0 ? g.p / g.n : null;
    const meanYards = g.yardsW > 0 ? g.yardsSum / g.yardsW : null;
    return {
      key,
      n_plays: g.n,
      n_pressure: g.p,
      pressure_rate: rate,
      mean_yards_allowed: meanYards,
      bpi: computeBpi(rate, meanYards),
    };
  });
}

export type DistanceLabel = 'Short' | 'Medium' | 'Long';

export const DISTANCE_LABELS: Record<string, DistanceLabel> = {
  Corto: 'Short',
  Medio: 'Medium',
  Largo: 'Long',
};

export const DXD_DOWNS = [1, 2, 3, 4] as const;
export const DXD_COLUMNS: { bucket: string; label: DistanceLabel }[] = [
  { bucket: 'Corto', label: 'Short' },
  { bucket: 'Medio', label: 'Medium' },
  { bucket: 'Largo', label: 'Long' },
];

export interface DxdCell {
  down: number;
  distanceBucket: string;
  distanceLabel: DistanceLabel;
  n_plays: number;
  n_pressure: number;
  pressure_rate: number | null;
  mean_yards_allowed: number | null;
  bpi: number | null;
}

export interface DxdMatrix {
  /** rows[downIndex][columnIndex]; null when zero plays or null bpi. */
  rows: (DxdCell | null)[][];
  /** max |bpi| over non-null cells (0 when there are none). */
  maxAbs: number;
}

export function buildDxd(cells: BpiDownDistanceCell[]): DxdMatrix {
  let maxAbs = 0;
  const rows = DXD_DOWNS.map((down) =>
    DXD_COLUMNS.map(({ bucket, label }) => {
      let n = 0;
      let p = 0;
      let yardsW = 0;
      let yardsSum = 0;
      for (const c of cells) {
        if (c.down !== down || c.distance_bucket !== bucket) continue;
        n += c.n_plays;
        p += c.n_pressure;
        if (c.mean_yards_allowed != null) {
          yardsW += c.n_plays;
          yardsSum += c.n_plays * c.mean_yards_allowed;
        }
      }
      if (n === 0) return null;
      const rate = p / n;
      const meanYards = yardsW > 0 ? yardsSum / yardsW : null;
      const bpi = computeBpi(rate, meanYards);
      if (bpi == null) return null;
      maxAbs = Math.max(maxAbs, Math.abs(bpi));
      const cell: DxdCell = {
        down,
        distanceBucket: bucket,
        distanceLabel: label,
        n_plays: n,
        n_pressure: p,
        pressure_rate: rate,
        mean_yards_allowed: meanYards,
        bpi,
      };
      return cell;
    }),
  );
  return { rows, maxAbs };
}

export interface BpiColor {
  hue: 'positive' | 'negative' | 'neutral';
  intensity: number; // [0, 1]
}

/** Diverging scale centered on 0: positive blue, negative red, 0 neutral. */
export function bpiColor(bpi: number | null, maxAbs: number): BpiColor | null {
  if (bpi == null) return null;
  if (bpi === 0 || maxAbs <= 0) return { hue: 'neutral', intensity: 0 };
  return {
    hue: bpi > 0 ? 'positive' : 'negative',
    intensity: Math.min(1, Math.abs(bpi) / maxAbs),
  };
}
