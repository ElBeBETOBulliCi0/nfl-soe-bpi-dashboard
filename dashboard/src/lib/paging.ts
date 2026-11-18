export const PAGE_SIZE = 25;

export function nextOffset(offset: number): number {
  return offset + PAGE_SIZE;
}

export function prevOffset(offset: number): number {
  return Math.max(0, offset - PAGE_SIZE);
}

export function hasNext(offset: number, total: number): boolean {
  return offset + PAGE_SIZE < total;
}

export function hasPrev(offset: number): boolean {
  return offset > 0;
}
