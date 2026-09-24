import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { getReferenceData } from '../api/referenceApi';


const REFERENCE_SECTIONS_BY_MODULE = {
  usuarios: ['usuarios', 'departamentos'],
  equipos: ['usuarios', 'departamentos'],
  anexos: ['usuarios'],
  perfiles: ['perfiles', 'departamentos'],
  departamentos: ['departamentos', 'usuarios', 'perfiles'],
  'pcs-genericos': ['departamentos'],
  ips: ['ips_stats'],
};


export const useReferenceData = (token, role, activeModule) => {
  const [usuariosList, setUsuariosList] = useState([]);
  const [ipsList, setIpsList] = useState([]);
  const [departamentosList, setDepartamentosList] = useState([]);
  const [perfilesList, setPerfilesList] = useState([]);
  const [ipSegmentStats, setIpSegmentStats] = useState({});
  const loadedSectionsRef = useRef(new Set());

  const clearReferenceData = useCallback(() => {
    setUsuariosList([]);
    setIpsList([]);
    setDepartamentosList([]);
    setPerfilesList([]);
    setIpSegmentStats({});
    loadedSectionsRef.current.clear();
  }, []);

  const loadReferenceData = useCallback(async (sections = [], force = false) => {
    if (!token || role === 'Visualizador') {
      clearReferenceData();
      return;
    }

    const requestedSections = sections.length
      ? [...new Set(sections)]
      : force
        ? ['usuarios', 'ips', 'departamentos', 'perfiles', 'ips_stats']
        : [];
    const pendingSections = force
      ? requestedSections
      : requestedSections.filter(
        (section) => !loadedSectionsRef.current.has(section)
      );

    if (pendingSections.length === 0) {
      return;
    }

    try {
      const result = await getReferenceData(pendingSections);

      if (Object.prototype.hasOwnProperty.call(result, 'usuarios')) {
        setUsuariosList(result.usuarios);
      }
      if (Object.prototype.hasOwnProperty.call(result, 'ips')) {
        setIpsList(result.ips);
      }
      if (Object.prototype.hasOwnProperty.call(result, 'departamentos')) {
        setDepartamentosList(result.departamentos);
      }
      if (Object.prototype.hasOwnProperty.call(result, 'perfiles')) {
        setPerfilesList(result.perfiles);
      }
      if (Object.prototype.hasOwnProperty.call(result, 'ips_stats')) {
        setIpSegmentStats(result.ips_stats);
      }

      Object.keys(result).forEach((section) => {
        loadedSectionsRef.current.add(section);
      });
    } catch (error) {
      console.error(
        'Error cargando datos de referencia:',
        error.response?.data || error
      );
    }
  }, [token, role, clearReferenceData]);

  const refreshReferenceData = useCallback(
    (sections = []) => loadReferenceData(sections, true),
    [loadReferenceData]
  );

  const ensureReferenceData = useCallback(
    (sections = []) => loadReferenceData(sections, false),
    [loadReferenceData]
  );

  useEffect(() => {
    const sections = REFERENCE_SECTIONS_BY_MODULE[activeModule] || [];
    ensureReferenceData(sections);
  }, [activeModule, ensureReferenceData]);

  const dptosList = useMemo(() => Array.from(
    new Set(
      departamentosList
        .map((departamento) => departamento.nombre)
        .filter(Boolean)
        .concat(
          usuariosList
            .map((usuario) => usuario.departamento_nombre || usuario.dpto_area)
            .filter(Boolean)
        )
    )
  ).sort((left, right) => (
    left.localeCompare(right, 'es', { sensitivity: 'base' })
  )), [departamentosList, usuariosList]);

  return {
    dptosList,
    usuariosList,
    ipsList,
    departamentosList,
    perfilesList,
    ipSegmentStats,
    refreshReferenceData,
    ensureReferenceData,
  };
};
