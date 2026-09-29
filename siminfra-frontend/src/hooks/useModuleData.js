import { useCallback, useEffect, useMemo, useState } from 'react';
import { getItemsByTab } from '../services/getItemService';


const PAGE_SIZE = 50;
const EXPORT_PAGE_SIZE = 200;
const EMPTY_PAGINATION = {
  count: 0,
  page: 1,
  pageSize: PAGE_SIZE,
  totalPages: 1,
};


const normalizeResponse = (response) => {
  if (Array.isArray(response)) {
    return {
      items: response,
      pagination: {
        ...EMPTY_PAGINATION,
        count: response.length,
        pageSize: response.length || PAGE_SIZE,
      },
    };
  }

  const items = Array.isArray(response?.results) ? response.results : [];
  return {
    items,
    pagination: {
      count: Number(response?.count) || 0,
      page: Number(response?.page) || 1,
      pageSize: Number(response?.page_size) || PAGE_SIZE,
      totalPages: Math.max(Number(response?.total_pages) || 1, 1),
    },
  };
};


export const useModuleData = ({
  token,
  tab,
  search,
  selectedDpto,
  equipmentCategory,
  selectedIpSegment,
  selectedEstadoEquipo,
  selectedEstadoIP,
  selectedEstadoAnexo,
  onUnauthorized,
  autoRefreshMs = 0,
  enabled = true,
}) => {
  const [data, setData] = useState([]);
  const [pagination, setPagination] = useState(EMPTY_PAGINATION);
  const [pageState, setPageState] = useState({ key: '', page: 1 });
  const [debouncedSearch, setDebouncedSearch] = useState(search.trim());
  const [loadedRequestKey, setLoadedRequestKey] = useState('');
  const normalizedSearch = search.trim();
  const searchIsDebouncing = normalizedSearch !== debouncedSearch;

  useEffect(() => {
    const timer = window.setTimeout(
      () => setDebouncedSearch(normalizedSearch),
      150
    );
    return () => window.clearTimeout(timer);
  }, [normalizedSearch]);

  const baseParams = useMemo(() => {
    const params = {};

    if (debouncedSearch) {
      params.search = debouncedSearch;
    }

    if (
      selectedDpto
      && ['usuarios', 'perfiles', 'pcs-genericos'].includes(tab)
    ) {
      params.dpto_area = selectedDpto;
    }

    if (tab === 'equipos' && equipmentCategory) {
      if (equipmentCategory === 'PERIFERICOS') {
        params.categoria = equipmentCategory;
      } else {
        params.tipo = equipmentCategory;
      }
    }

    if (tab === 'ips' && selectedIpSegment) {
      params.segmento = selectedIpSegment;
    }

    if (selectedEstadoIP && tab === 'ips') {
      params.estado = selectedEstadoIP;
    }
    if (selectedEstadoEquipo && tab === 'equipos') {
      params.estado = selectedEstadoEquipo;
    }
    if (selectedEstadoAnexo && tab === 'anexos') {
      params.estado = selectedEstadoAnexo;
    }

    return params;
  }, [
    debouncedSearch,
    tab,
    selectedDpto,
    equipmentCategory,
    selectedIpSegment,
    selectedEstadoEquipo,
    selectedEstadoIP,
    selectedEstadoAnexo,
  ]);

  const filterKey = useMemo(
    () => JSON.stringify([tab, enabled, baseParams]),
    [tab, enabled, baseParams]
  );
  const page = pageState.key === filterKey ? pageState.page : 1;
  const requestKey = JSON.stringify([filterKey, page]);
  const isLoading = Boolean(
    token
    && enabled
    && (searchIsDebouncing || loadedRequestKey !== requestKey)
  );

  const exportParams = useMemo(() => {
    const params = { ...baseParams };
    if (normalizedSearch) {
      params.search = normalizedSearch;
    } else {
      delete params.search;
    }
    return params;
  }, [baseParams, normalizedSearch]);

  const setPage = useCallback((nextPage) => {
    const normalizedPage = Math.max(Number(nextPage) || 1, 1);
    setPageState({ key: filterKey, page: normalizedPage });
  }, [filterKey]);

  const loadData = useCallback(async (signal) => {
    if (!token || !enabled || searchIsDebouncing) {
      return null;
    }

    try {
      const result = await getItemsByTab(tab, {
        ...baseParams,
        page,
        page_size: PAGE_SIZE,
      }, { signal });
      return normalizeResponse(result);
    } catch (error) {
      if (
        error.code === 'ERR_CANCELED'
        || error.name === 'CanceledError'
        || error.name === 'AbortError'
      ) {
        return null;
      }

      if (error.response?.status === 401) {
        onUnauthorized?.();
        return null;
      }

      console.error(
        'Error cargando datos:',
        error.response?.data || error
      );
      return null;
    }
  }, [
    token,
    enabled,
    tab,
    baseParams,
    page,
    onUnauthorized,
    searchIsDebouncing,
  ]);

  const applyData = useCallback((normalized) => {
    if (!normalized) {
      return;
    }

    setData(normalized.items);
    setPagination(normalized.pagination);

    if (page > normalized.pagination.totalPages) {
      setPage(normalized.pagination.totalPages);
    }
  }, [page, setPage]);

  const refreshData = useCallback(async () => {
    const normalized = await loadData();
    applyData(normalized);
  }, [loadData, applyData]);

  const getAllData = useCallback(async () => {
    if (!token) {
      return [];
    }

    const allRows = [];
    let exportPage = 1;
    let totalPages = 1;

    do {
      const response = await getItemsByTab(tab, {
        ...exportParams,
        page: exportPage,
        page_size: EXPORT_PAGE_SIZE,
      });
      const normalized = normalizeResponse(response);
      allRows.push(...normalized.items);
      totalPages = normalized.pagination.totalPages;
      exportPage += 1;
    } while (exportPage <= totalPages);

    return allRows;
  }, [token, tab, exportParams]);

  useEffect(() => {
    if (!token || !enabled) {
      return;
    }

    if (searchIsDebouncing) {
      return;
    }

    const controller = new AbortController();

    loadData(controller.signal)
      .then((normalized) => {
        if (!controller.signal.aborted) {
          applyData(normalized);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoadedRequestKey(requestKey);
        }
      });

    return () => {
      controller.abort();
    };
  }, [
    token,
    enabled,
    normalizedSearch,
    searchIsDebouncing,
    requestKey,
    loadData,
    applyData,
  ]);

  useEffect(() => {
    if (!token || !enabled || !autoRefreshMs) {
      return undefined;
    }

    const intervalId = window.setInterval(refreshData, autoRefreshMs);
    const onFocus = () => refreshData();
    window.addEventListener('focus', onFocus);

    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener('focus', onFocus);
    };
  }, [token, enabled, autoRefreshMs, refreshData]);

  return {
    data: token && enabled ? data : [],
    pagination: token && enabled ? pagination : EMPTY_PAGINATION,
    setPage,
    refreshData,
    getAllData,
    isLoading,
  };
};
