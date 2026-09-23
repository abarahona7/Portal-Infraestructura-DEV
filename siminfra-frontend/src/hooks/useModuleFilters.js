import { useState } from 'react';

export const useModuleFilters = () => {
  const [search, setSearch] = useState('');
  const [selectedDpto, setSelectedDpto] = useState('');
  const [selectedCategoriaEquipo, setSelectedCategoriaEquipo] = useState('');
  const [selectedEstadoEquipo, setSelectedEstadoEquipo] = useState('');
  const [selectedEstadoIP, setSelectedEstadoIP] = useState('');
  const [selectedEstadoAnexo, setSelectedEstadoAnexo] = useState('');

  const resetFilters = () => {
    setSearch('');
    setSelectedDpto('');
    setSelectedCategoriaEquipo('');
    setSelectedEstadoEquipo('');
    setSelectedEstadoIP('');
    setSelectedEstadoAnexo('');
  };

  return {
    search,
    setSearch,

    selectedDpto,
    setSelectedDpto,

    selectedCategoriaEquipo,
    setSelectedCategoriaEquipo,

    selectedEstadoEquipo,
    setSelectedEstadoEquipo,

    selectedEstadoIP,
    setSelectedEstadoIP,

    selectedEstadoAnexo,
    setSelectedEstadoAnexo,

    resetFilters,
  };
};
