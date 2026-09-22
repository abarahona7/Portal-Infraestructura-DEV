import { useCallback, useEffect, useState } from 'react';

import { getUsuarios } from '../api/usuariosApi';
import { getIps } from '../api/ipsApi';
import { getDepartamentos } from '../api/departamentosApi';

export const useReferenceData = (token, role) => {
  const [dptosList, setDptosList] = useState([]);
  const [usuariosList, setUsuariosList] = useState([]);
  const [ipsList, setIpsList] = useState([]);
  const [departamentosList, setDepartamentosList] = useState([]);

  const refreshReferenceData = useCallback(async () => {
    if (!token) {
      setDptosList([]);
      setUsuariosList([]);
      setIpsList([]);
      setDepartamentosList([]);
      return;
    }

    // El Visualizador no necesita datos de Usuarios/IP y el backend
    // tampoco le permite consultar esos módulos.
    if (role === 'Visualizador') {
      setDptosList([]);
      setUsuariosList([]);
      setIpsList([]);
      setDepartamentosList([]);
      return;
    }

    try {
      const [usuarios, ips, departamentos] = await Promise.all([
        getUsuarios(),
        getIps(),
        getDepartamentos(),
      ]);

      setUsuariosList(usuarios);
      setIpsList(ips);
      setDepartamentosList(departamentos);

      const nombresDepartamentos = Array.from(
        new Set(
          departamentos
            .map((departamento) => departamento.nombre)
            .filter(Boolean)
            .concat(
              usuarios
                .map((usuario) => usuario.departamento_nombre || usuario.dpto_area)
                .filter(Boolean)
            )
        )
      ).sort((a, b) =>
        a.localeCompare(b, 'es', { sensitivity: 'base' })
      );

      setDptosList(nombresDepartamentos);
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
    departamentosList,
    refreshReferenceData,
  };
};
