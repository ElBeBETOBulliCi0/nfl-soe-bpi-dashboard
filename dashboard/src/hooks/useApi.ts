import { useCallback, useEffect, useRef, useState } from 'react';
import type { DependencyList } from 'react';

export type ApiStatus = 'loading' | 'empty' | 'error' | 'ready';

export interface UseApiResult<T> {
  status: ApiStatus;
  data: T | undefined;
  error: unknown;
  retry: () => void;
}

/**
 * Runs `fetcher` whenever `deps` change and tracks loading/empty/error/ready.
 * Each run gets an increasing request id; only the latest response is applied,
 * so superseded responses are discarded. `retry` re-runs only this hook.
 * `isEmpty` is a per-section predicate on the response data.
 */
export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: DependencyList,
  isEmpty?: (data: T) => boolean,
): UseApiResult<T> {
  const [state, setState] = useState<{ status: ApiStatus; data: T | undefined; error: unknown }>({
    status: 'loading',
    data: undefined,
    error: undefined,
  });
  const [attempt, setAttempt] = useState(0);
  const latestId = useRef(0);
  const fetcherRef = useRef(fetcher);
  const isEmptyRef = useRef(isEmpty);
  fetcherRef.current = fetcher;
  isEmptyRef.current = isEmpty;

  useEffect(() => {
    const id = ++latestId.current;
    setState((s) => ({ status: 'loading', data: s.data, error: undefined }));
    fetcherRef
      .current()
      .then((data) => {
        if (id !== latestId.current) return;
        const empty = isEmptyRef.current ? isEmptyRef.current(data) : false;
        setState({ status: empty ? 'empty' : 'ready', data, error: undefined });
      })
      .catch((error: unknown) => {
        if (id !== latestId.current) return;
        setState({ status: 'error', data: undefined, error });
      });
    return () => {
      // Invalidate this request when deps change or the component unmounts.
      if (latestId.current === id) latestId.current = id + 1;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  return { status: state.status, data: state.data, error: state.error, retry };
}
