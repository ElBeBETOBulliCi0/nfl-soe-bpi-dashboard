import type { PlayDetailResponse } from '../api/types';

export interface ReceiverLine {
  nflId: number;
  name: string;
  isTarget: boolean;
  rx: number; // receiver at release frame
  ry: number;
  dx: number | null; // nearest Coverage player, null when none
  dy: number | null;
  separation: number | null; // route.separation (yards)
  expected: number | null;
  soe: number | null;
}

export function pairReceivers(detail: PlayDetailResponse): ReceiverLine[] {
  const cover = detail.players.filter(
    (p) => p.pff_role === 'Coverage' && p.x != null && p.y != null,
  );
  return detail.routes.flatMap((r): ReceiverLine[] => {
    const rec = detail.players.find((p) => p.nflId === r.nflId);
    if (!rec || rec.x == null || rec.y == null) return []; // no coordinates: no marker
    let bx: number | null = null;
    let by: number | null = null;
    let bestD = Infinity;
    for (const c of cover) {
      const d = Math.hypot((c.x as number) - rec.x, (c.y as number) - rec.y);
      if (d < bestD) {
        bestD = d;
        bx = c.x;
        by = c.y;
      }
    }
    // Likely target: use the backend nearest_defender when present (single source).
    const nd = detail.nearest_defender;
    if (r.is_likely_target && nd && nd.x != null && nd.y != null) {
      bx = nd.x;
      by = nd.y;
    }
    return [
      {
        nflId: r.nflId,
        name: r.displayName ?? String(r.nflId),
        isTarget: r.is_likely_target,
        rx: rec.x,
        ry: rec.y,
        dx: bx,
        dy: by,
        separation: r.separation,
        expected: r.expected_separation,
        soe: r.soe,
      },
    ];
  });
}
