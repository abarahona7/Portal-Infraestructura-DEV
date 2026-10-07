import { useState } from 'react';

export const useModuleFilters = () => {
  const [search, setSearch] = useState('');
  const [selectedDpto, setSelectedDpto] = useState('');
  const [selectedCategoriaEquipo, setSelectedCategoriaEquipo] = useState('');
  const [selectedEstadoIP, setSelectedEstadoIP] = useState('');
  const [selectedEstadoAnexo, setSelectedEstadoAnexo] = useState('');
  const [selectedEstadoGeneral, setSelectedEstadoGeneral] = useState('');

  const resetFilters = () => {
    setSearch('');
    setSelectedDpto('');
    setSelectedCategoriaEquipo('');
    setSelectedEstadoIP('');
    setSelectedEstadoAnexo('');
    setSelectedEstadoGeneral('');
  };

  return {
    search,
    setSearch,

    selectedDpto,
    setSelectedDpto,

    selectedCategoriaEquipo,
    setSelectedCategoriaEquipo,

    selectedEstadoIP,
    setSelectedEstadoIP,

    selectedEstadoAnexo,
    setSelectedEstadoAnexo,

    selectedEstadoGeneral,
    setSelectedEstadoGeneral,

    resetFilters,
  };
};
