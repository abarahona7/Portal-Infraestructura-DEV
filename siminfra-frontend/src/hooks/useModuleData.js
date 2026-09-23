import { useCallback, useEffect, useState } from 'react';
import { getItemsByTab } from '../services/getItemService';

export const useModuleData = ({
  token,
  tab,
  search,
  selectedDpto,
  selectedEstadoEquipo,
  selectedEstadoIP,
  selectedEstadoAnexo,
  onUnauthorized,
  autoRefreshMs = 0,
}) => {
  const [data, setData] = useState([]);

  const refreshData = useCallback(async () => {
    if (!token) {
      setData([]);
      return;
    }

    try {
      const params = {};

      if (search) {
        params.search = search;
      }

      if (
        selectedDpto &&
        (
          tab === 'usuarios' ||
          tab === 'perfiles' ||
          tab === 'pcs-genericos'
        )
      ) {
        params.dpto_area = selectedDpto;
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

      const result = await getItemsByTab(tab, params);
      setData(result);
    } catch (error) {
      if (error.response?.status === 401) {
        onUnauthorized?.();
        return;
      }

      console.error(
        'Error cargando datos:',
        error.response?.data || error
      );
    }
  }, [
    token,
    tab,
    search,
    selectedDpto,
    selectedEstadoEquipo,
    selectedEstadoIP,
    selectedEstadoAnexo,
    onUnauthorized,
  ]);

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  // Para vistas de consulta (especialmente Visualizador/Anexos), permite
  // reflejar cambios realizados por un Administrador sin reingresar.
  useEffect(() => {
    if (!token || !autoRefreshMs) {
      return undefined;
    }

    const intervalId = window.setInterval(refreshData, autoRefreshMs);
    const onFocus = () => refreshData();

    window.addEventListener('focus', onFocus);

    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener('focus', onFocus);
    };
  }, [token, autoRefreshMs, refreshData]);

  return {
    data,
    refreshData,
  };
};
