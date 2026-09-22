import { useCallback, useEffect, useState } from 'react';

import { getUsuarios } from '../api/usuariosApi';
import { getIps } from '../api/ipsApi';
import { getDepartamentos } from '../api/departamentosApi';
import { getPerfiles } from '../api/perfilesApi';

export const useReferenceData = (token, role) => {
  const [dptosList, setDptosList] = useState([]);
  const [usuariosList, setUsuariosList] = useState([]);
  const [ipsList, setIpsList] = useState([]);
  const [departamentosList, setDepartamentosList] = useState([]);
  const [perfilesList, setPerfilesList] = useState([]);

  const refreshReferenceData = useCallback(async () => {
    if (!token) {
      setDptosList([]);
      setUsuariosList([]);
      setIpsList([]);
      setDepartamentosList([]);
      setPerfilesList([]);
      return;
    }

    // El Visualizador no necesita datos de Usuarios/IP y el backend
    // tampoco le permite consultar esos módulos.
    if (role === 'Visualizador') {
      setDptosList([]);
      setUsuariosList([]);
      setIpsList([]);
      setDepartamentosList([]);
      setPerfilesList([]);
      return;
    }

    try {
      const [usuarios, ips, departamentos, perfiles] = await Promise.all([
        getUsuarios(),
        getIps(),
        getDepartamentos(),
        getPerfiles(),
      ]);

      setUsuariosList(usuarios);
      setIpsList(ips);
      setDepartamentosList(departamentos);
      setPerfilesList(perfiles);

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
    perfilesList,
    refreshReferenceData,
  };
};
