import { useCallback, useEffect, useState } from 'react';

import { getUsuarios } from '../api/usuariosApi';
import { getIps } from '../api/ipsApi';

export const useReferenceData = (token, role) => {
  const [dptosList, setDptosList] = useState([]);
  const [usuariosList, setUsuariosList] = useState([]);
  const [ipsList, setIpsList] = useState([]);

  const refreshReferenceData = useCallback(async () => {
    if (!token) {
      setDptosList([]);
      setUsuariosList([]);
      setIpsList([]);
      return;
    }

    // El Visualizador no necesita datos de Usuarios/IP y el backend
    // tampoco le permite consultar esos módulos.
    if (role === 'Visualizador') {
      setDptosList([]);
      setUsuariosList([]);
      setIpsList([]);
      return;
    }

    try {
      const [usuarios, ips] = await Promise.all([
        getUsuarios(),
        getIps(),
      ]);

      setUsuariosList(usuarios);
      setIpsList(ips);

      const departamentos = Array.from(
        new Set(
          usuarios
            .map((usuario) => usuario.dpto_area)
            .filter(Boolean)
        )
      ).sort();

      setDptosList(departamentos);
    } catch (error) {
      console.error(
        'Error cargando datos de referencia:',
        error.response?.data || error
      );
    }
  }, [token, role]);

  useEffect(() => {
    refreshReferenceData();
  }, [refreshReferenceData]);

  return {
    dptosList,
    usuariosList,
    ipsList,
    refreshReferenceData,
  };
};
