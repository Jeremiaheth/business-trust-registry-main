import { useEffect, useState } from "react";

interface UseApiState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

export function useApi<T>(loader: () => Promise<T>, dependencies: unknown[]): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    loader()
      .then((value) => {
        if (!cancelled) {
          setData(value);
        }
      })
      .catch((loadError: Error) => {
        if (!cancelled) {
          setError(loadError.message);
          setData(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, dependencies);

  return { data, error, loading };
}
