export const ALL = 'Todos';

export type QueryValue = string | number | boolean | undefined;
export type Query = Record<string, QueryValue>;

/** SOE tab filters. Select values hold "Todos" or a backend value. */
export interface SoeFilters {
  coverage: string;
  coverageType: string;
  position: string;
  onlyTargets: boolean;
  selectedReceiver: number | undefined;
}

/** BPI tab filters. Select values hold "Todos" or a backend value. */
export interface BpiFilters {
  down: string;
  distanceBucket: string;
  numRushers: string;
  coverage: string;
}

export const initialSoeFilters: SoeFilters = {
  coverage: ALL,
  coverageType: ALL,
  position: ALL,
  onlyTargets: false,
  selectedReceiver: undefined,
};

export const initialBpiFilters: BpiFilters = {
  down: ALL,
  distanceBucket: ALL,
  numRushers: ALL,
  coverage: ALL,
};

function val(v: string): string | undefined {
  return v === ALL || v === '' ? undefined : v;
}

/** Query params for the SOE endpoints. Omits "Todos"; `only_targets` only when on. */
export function soeToQuery(f: SoeFilters): Query {
  return {
    coverage: val(f.coverage),
    coverage_type: val(f.coverageType),
    position: val(f.position),
    only_targets: f.onlyTargets ? true : undefined,
  };
}

/** Query params for the BPI endpoint. Omits "Todos". */
export function bpiToQuery(f: BpiFilters): Query {
  return {
    down: val(f.down),
    distance_bucket: val(f.distanceBucket),
    num_rushers: val(f.numRushers),
    coverage: val(f.coverage),
  };
}

export function toQuery(f: SoeFilters | BpiFilters): Query {
  return 'onlyTargets' in f ? soeToQuery(f) : bpiToQuery(f);
}

/** Resets all filters of a tab to "Todos" and clears the selected receiver. */
export function resetSoeFilters(): SoeFilters {
  return { ...initialSoeFilters };
}

export function resetBpiFilters(): BpiFilters {
  return { ...initialBpiFilters };
}

export function resetFilters<T extends SoeFilters | BpiFilters>(f: T): T {
  return ('onlyTargets' in f ? resetSoeFilters() : resetBpiFilters()) as T;
}

/** Selection toggle: selecting the selected id again clears it. */
export function toggle(prev: number | undefined, id: number): number | undefined {
  return prev === id ? undefined : id;
}
