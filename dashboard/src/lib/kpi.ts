import type { BpiSummaryResponse, HeatmapCell, PlayerSoe } from '../api/types';

export interface SoeKpis {
  routes: number;
  meanSoe: number | null;
  meanSep: number | null;
  receivers: number;
}

export interface BpiKpis {
  totalPlays: number;
  pressureRate: number | null;
  meanYardsAllowed: number | null;
  totalPressures: number;
}

/** Mean of `pick(cell)` weighted by `n`, using only cells with a non-null value. Null when weight is 0. */
function weightedMean(
  cells: HeatmapCell[],
  pick: (c: HeatmapCell) => number | null,
): number | null {
  let weight = 0;
  let sum = 0;
  for (const c of cells) {
    const v = pick(c);
    if (v == null) continue;
    weight += c.n;
    sum += c.n * v;
  }
  return weight > 0 ? sum / weight : null;
}

export function soeKpis(cells: HeatmapCell[], players: PlayerSoe[]): SoeKpis {
  return {
    routes: cells.reduce((acc, c) => acc + c.n, 0),
    meanSoe: weightedMean(cells, (c) => c.mean_soe),
    meanSep: weightedMean(cells, (c) => c.mean_separation),
    receivers: players.length,
  };
}

export function bpiKpis(summary: BpiSummaryResponse): BpiKpis {
  return {
    totalPlays: summary.total_plays,
    pressureRate: summary.pressure_rate,
    meanYardsAllowed: summary.mean_yards_allowed,
    totalPressures: summary.by_rushers.reduce((acc, r) => acc + r.n_pressure, 0),
  };
}
