// API client: one function per endpoint. All URLs are relative and start with "api/"
// (no leading slash) so the app works when published under a sub-path.
// Filter state types and their query mapping live in lib/filters.ts (single source of truth).

import { bpiToQuery, soeToQuery } from '../lib/filters';
import type { BpiFilters, SoeFilters } from '../lib/filters';
import type {
  BpiSummaryResponse,
  FiltersResponse,
  HeatmapResponse,
  PlayDetailResponse,
  PlayersResponse,
  PlaysResponse,
} from './types';

export type { BpiFilters, SoeFilters };

export type QueryParams = Record<string, string | number | boolean | undefined>;

/** Optional backend parameters not held in the filter state. Undefined values are omitted. */
export interface ExtraParams {
  team?: string;
  week?: number;
  search?: string;
  minN?: number;
  limit?: number;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number) {
    super(`HTTP ${status}`);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function buildUrl(path: string, params: QueryParams): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined) qs.set(k, String(v));
  }
  const s = qs.toString();
  return s ? `${path}?${s}` : path;
}

async function request<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new ApiError(res.status);
  return (await res.json()) as T;
}

function nonEmpty(v: string | undefined): string | undefined {
  return v === undefined || v === '' ? undefined : v;
}

export const getFilters = () => request<FiltersResponse>('api/filters');

export const getHeatmap = (f: SoeFilters, x: ExtraParams = {}) =>
  request<HeatmapResponse>(
    buildUrl('api/soe/heatmap', { ...soeToQuery(f), team: nonEmpty(x.team), week: x.week }),
  );

export const getPlayers = (f: SoeFilters, x: ExtraParams = {}) =>
  request<PlayersResponse>(
    buildUrl('api/soe/players', {
      ...soeToQuery(f),
      team: nonEmpty(x.team),
      week: x.week,
      search: nonEmpty(x.search),
      min_n: x.minN,
      limit: x.limit ?? 20,
    }),
  );

export const getPlays = (
  f: SoeFilters,
  player: number | undefined,
  offset: number,
  x: ExtraParams = {},
) =>
  request<PlaysResponse>(
    buildUrl('api/soe/plays', {
      ...soeToQuery(f),
      team: nonEmpty(x.team),
      week: x.week,
      player,
      limit: x.limit ?? 25,
      offset,
    }),
  );

export const getPlay = (gameId: number, playId: number) =>
  request<PlayDetailResponse>(`api/soe/play/${gameId}/${playId}`);

export const getBpiSummary = (f: BpiFilters, x: ExtraParams = {}) =>
  request<BpiSummaryResponse>(
    buildUrl('api/bpi/summary', { ...bpiToQuery(f), team: nonEmpty(x.team) }),
  );
