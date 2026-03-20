import { useState, useEffect, useCallback } from "react";
import api from "../utils/api";

/**
 * Custom hook for API calls with loading, error, and data states.
 *
 * Usage:
 *   const { data, loading, error, refetch } = useApi("/claims");
 *   const { execute } = useApi("/claims", { manual: true, method: "post" });
 */
export default function useApi(url, options = {}) {
  const {
    manual = false,
    method = "get",
    body = null,
    params = null,
    initialData = null,
  } = options;

  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(!manual);
  const [error, setError] = useState(null);

  const execute = useCallback(
    async (overrideBody = null, overrideParams = null) => {
      setLoading(true);
      setError(null);
      try {
        const config = {
          method,
          url,
          ...(method === "get"
            ? { params: overrideParams || params }
            : { data: overrideBody || body, params: overrideParams || params }),
        };
        const response = await api(config);
        setData(response.data);
        return response.data;
      } catch (err) {
        const message =
          err.response?.data?.detail ||
          err.response?.data?.message ||
          err.message ||
          "An unexpected error occurred";
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [url, method, body, params]
  );

  const refetch = useCallback(() => execute(), [execute]);

  useEffect(() => {
    if (!manual) {
      execute();
    }
  }, [manual, execute]);

  return { data, loading, error, refetch, execute };
}
